from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import DistributedLock
from app.core.crud import bad_request, not_found, paginate
from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import (
    STATUS_CANCELLED,
    STATUS_DRAFT,
    STATUS_EXECUTED,
    Goods,
    Location,
    SysUser,
    TransferItem,
    TransferOrder,
    Warehouse,
)
from app.schemas.order import TransferCreate, TransferOut
from app.services.inventory import apply_stock_change, generate_order_no

router = APIRouter(prefix="/transfer/orders", tags=["仓库调拨"])


def apply_scope(stmt, scope):
    if scope is None:
        return stmt
    if not scope:
        return stmt.where(TransferOrder.from_warehouse_id.in_([-1]))
    return stmt.where(TransferOrder.from_warehouse_id.in_(scope))


async def _detail(db: AsyncSession, order: TransferOrder, items: list[TransferItem]) -> dict:
    goods_ids = {i.goods_id for i in items} or {0}
    loc_ids = {i.from_location_id for i in items} | {i.to_location_id for i in items} or {0}
    goods_map = {g.id: g for g in (await db.execute(select(Goods).where(Goods.id.in_(goods_ids)))).scalars().all()}
    loc_map = {l.id: l for l in (await db.execute(select(Location).where(Location.id.in_(loc_ids)))).scalars().all()}
    from_wh, to_wh = await db.get(Warehouse, order.from_warehouse_id), await db.get(Warehouse, order.to_warehouse_id)
    data = TransferOut.model_validate(order).model_dump()
    data["from_warehouse_name"] = from_wh.name if from_wh else ""
    data["to_warehouse_name"] = to_wh.name if to_wh else ""
    data["items"] = [
        {
            "id": i.id,
            "goods_id": i.goods_id,
            "from_location_id": i.from_location_id,
            "to_location_id": i.to_location_id,
            "qty": float(i.qty),
            "goods_name": goods_map[i.goods_id].name if i.goods_id in goods_map else "",
            "goods_code": goods_map[i.goods_id].code if i.goods_id in goods_map else "",
            "from_location_code": loc_map[i.from_location_id].code if i.from_location_id in loc_map else "",
            "to_location_code": loc_map[i.to_location_id].code if i.to_location_id in loc_map else "",
        }
        for i in items
    ]
    return data


@router.get("", dependencies=[Depends(require_perm("inventory:transfer:list"))])
async def list_transfers(
    keyword: str = "",
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = select(TransferOrder).order_by(TransferOrder.id.desc())
    stmt = apply_scope(stmt, get_warehouse_scope(current))
    if keyword:
        stmt = stmt.where(TransferOrder.order_no.contains(keyword))
    if status:
        stmt = stmt.where(TransferOrder.status == status)
    total, orders = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": [await _detail(db, o, []) for o in orders]}


@router.get("/{order_id}")
async def get_transfer(order_id: int, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(TransferOrder).where(TransferOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("调拨单不存在")
    items = (await db.execute(select(TransferItem).where(TransferItem.order_id == order_id))).scalars().all()
    return await _detail(db, order, items)


@router.post("", dependencies=[Depends(require_perm("inventory:transfer:create"))])
async def create_transfer(body: TransferCreate, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    if body.from_warehouse_id == body.to_warehouse_id:
        raise bad_request("源仓库与目标仓库不能相同")
    if not body.items:
        raise bad_request("调拨明细不能为空")
    # 校验库位归属
    loc_ids = {i.from_location_id for i in body.items} | {i.to_location_id for i in body.items}
    locs = (await db.execute(select(Location).where(Location.id.in_(list(loc_ids))))).scalars().all()
    loc_map = {l.id: l for l in locs}
    for i in body.items:
        fl, tl = loc_map.get(i.from_location_id), loc_map.get(i.to_location_id)
        if not fl or not tl:
            raise bad_request("库位不存在")
        if fl.warehouse_id != body.from_warehouse_id:
            raise bad_request(f"源库位 {fl.code} 不属于源仓库")
        if tl.warehouse_id != body.to_warehouse_id:
            raise bad_request(f"目标库位 {tl.code} 不属于目标仓库")
        if i.qty <= 0:
            raise bad_request("数量必须大于 0")

    order_no = await generate_order_no(db, "TR")
    order = TransferOrder(
        order_no=order_no,
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        status=STATUS_DRAFT,
        remark=body.remark,
        creator_id=current.id,
        creator_name=current.nickname or current.username,
    )
    db.add(order)
    await db.flush()
    for i in body.items:
        db.add(TransferItem(order_id=order.id, **i.model_dump()))
    await db.commit()
    return await get_transfer(order.id, db)


@router.post("/{order_id}/execute", dependencies=[Depends(require_perm("inventory:transfer:execute"))])
async def execute_transfer(order_id: int, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """执行调拨：源仓扣 + 目标仓加，Redis 分布式锁保证跨仓原子性。"""
    order = (await db.execute(select(TransferOrder).where(TransferOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("调拨单不存在")
    if order.status != STATUS_DRAFT:
        raise bad_request("仅草稿状态可执行")
    items = (await db.execute(select(TransferItem).where(TransferItem.order_id == order_id))).scalars().all()

    lock_key = f"transfer:{min(order.from_warehouse_id, order.to_warehouse_id)}:{max(order.from_warehouse_id, order.to_warehouse_id)}"
    try:
        async with DistributedLock(lock_key):
            for i in items:
                await apply_stock_change(
                    db, goods_id=i.goods_id, warehouse_id=order.from_warehouse_id, location_id=i.from_location_id,
                    qty_change=-float(i.qty), biz_type="transfer_out", order_no=order.order_no,
                    operator_id=current.id, operator_name=current.nickname or current.username,
                )
                await apply_stock_change(
                    db, goods_id=i.goods_id, warehouse_id=order.to_warehouse_id, location_id=i.to_location_id,
                    qty_change=float(i.qty), biz_type="transfer_in", order_no=order.order_no,
                    operator_id=current.id, operator_name=current.nickname or current.username,
                )
            order.status = STATUS_EXECUTED
            order.executed_at = datetime.now()
            await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await get_transfer(order_id, db)


@router.post("/{order_id}/cancel", dependencies=[Depends(require_perm("inventory:transfer:cancel"))])
async def cancel_transfer(order_id: int, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(TransferOrder).where(TransferOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found()
    if order.status == STATUS_EXECUTED:
        raise bad_request("已执行单据不可作废")
    if order.status == STATUS_CANCELLED:
        raise bad_request("单据已作废")
    order.status = STATUS_CANCELLED
    await db.commit()
    return await get_transfer(order_id, db)
