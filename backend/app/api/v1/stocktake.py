from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import bad_request, not_found, paginate
from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import (
    Goods,
    Inventory,
    InventoryTransaction,
    Location,
    StocktakeItem,
    StocktakeOrder,
    SysUser,
    Warehouse,
    Zone,
)
from app.schemas.order import StocktakeCreate, StocktakeRecordIn
from app.services.inventory import apply_stock_change, generate_order_no

router = APIRouter(prefix="/stocktake/orders", tags=["盘点管理"])


def apply_scope(stmt, scope):
    if scope is None:
        return stmt
    if not scope:
        return stmt.where(StocktakeOrder.warehouse_id.in_([-1]))
    return stmt.where(StocktakeOrder.warehouse_id.in_(scope))


async def _detail(db: AsyncSession, order: StocktakeOrder) -> dict:
    wh = await db.get(Warehouse, order.warehouse_id)
    zone = await db.get(Zone, order.zone_id) if order.zone_id else None
    item_count = (
        await db.execute(select(func.count()).select_from(StocktakeItem).where(StocktakeItem.order_id == order.id))
    ).scalar_one()
    diff_count = (
        await db.execute(
            select(func.count()).select_from(StocktakeItem).where(
                StocktakeItem.order_id == order.id,
                StocktakeItem.actual_qty.is_not(None),
                StocktakeItem.actual_qty != StocktakeItem.book_qty,
            )
        )
    ).scalar_one()
    return {
        "id": order.id,
        "order_no": order.order_no,
        "warehouse_id": order.warehouse_id,
        "zone_id": order.zone_id,
        "status": order.status,
        "remark": order.remark,
        "creator_name": order.creator_name,
        "finished_at": order.finished_at,
        "created_at": order.created_at,
        "warehouse_name": wh.name if wh else "",
        "zone_name": zone.name if zone else "全仓",
        "item_count": item_count,
        "diff_count": diff_count,
    }


@router.get("", dependencies=[Depends(require_perm("stocktake:order:list"))])
async def list_stocktakes(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = select(StocktakeOrder).order_by(StocktakeOrder.id.desc())
    stmt = apply_scope(stmt, get_warehouse_scope(current))
    if status:
        stmt = stmt.where(StocktakeOrder.status == status)
    total, orders = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": [await _detail(db, o) for o in orders]}


@router.get("/{order_id}", dependencies=[Depends(require_perm("stocktake:order:list"))])
async def get_stocktake(order_id: int, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(StocktakeOrder).where(StocktakeOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("盘点单不存在")
    items = (await db.execute(select(StocktakeItem).where(StocktakeItem.order_id == order_id))).scalars().all()
    goods_ids = {i.goods_id for i in items} or {0}
    loc_ids = {i.location_id for i in items} or {0}
    goods_map = {g.id: g for g in (await db.execute(select(Goods).where(Goods.id.in_(goods_ids)))).scalars().all()}
    loc_map = {l.id: l for l in (await db.execute(select(Location).where(Location.id.in_(loc_ids)))).scalars().all()}
    data = await _detail(db, order)
    data["items"] = [
        {
            "id": i.id,
            "goods_id": i.goods_id,
            "location_id": i.location_id,
            "book_qty": float(i.book_qty),
            "actual_qty": float(i.actual_qty) if i.actual_qty is not None else None,
            "goods_name": goods_map[i.goods_id].name if i.goods_id in goods_map else "",
            "goods_code": goods_map[i.goods_id].code if i.goods_id in goods_map else "",
            "location_code": loc_map[i.location_id].code if i.location_id in loc_map else "",
        }
        for i in items
    ]
    return data


@router.post("", dependencies=[Depends(require_perm("stocktake:order:create"))])
async def create_stocktake(body: StocktakeCreate, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """创建盘点单：按仓库/库区范围快照当前库存账面数量。"""
    stmt = select(Inventory).where(Inventory.warehouse_id == body.warehouse_id, Inventory.qty > 0)
    if body.zone_id:
        loc_ids = select(Location.id).where(Location.zone_id == body.zone_id, Location.is_deleted.is_(False))
        stmt = stmt.where(Inventory.location_id.in_(loc_ids))
    balances = (await db.execute(stmt)).scalars().all()
    if not balances:
        raise bad_request("盘点范围内没有库存")

    order_no = await generate_order_no(db, "ST")
    order = StocktakeOrder(
        order_no=order_no,
        warehouse_id=body.warehouse_id,
        zone_id=body.zone_id,
        status="processing",
        remark=body.remark,
        creator_id=current.id,
        creator_name=current.nickname or current.username,
    )
    db.add(order)
    await db.flush()
    for b in balances:
        db.add(StocktakeItem(order_id=order.id, goods_id=b.goods_id, location_id=b.location_id, book_qty=b.qty))
    await db.commit()
    return await get_stocktake(order.id, db)


@router.post("/{order_id}/record", dependencies=[Depends(require_perm("stocktake:order:update"))])
async def record_stocktake(order_id: int, records: list[StocktakeRecordIn], db: AsyncSession = Depends(get_db)):
    """录入实盘数量（可分批录入）。"""
    order = (await db.execute(select(StocktakeOrder).where(StocktakeOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("盘点单不存在")
    if order.status != "processing":
        raise bad_request("盘点单不在进行中")
    items = {i.id: i for i in (await db.execute(select(StocktakeItem).where(StocktakeItem.order_id == order_id))).scalars().all()}
    for r in records:
        item = items.get(r.item_id)
        if not item:
            raise bad_request(f"明细不存在：{r.item_id}")
        item.actual_qty = r.actual_qty
    await db.commit()
    return await get_stocktake(order_id, db)


@router.post("/{order_id}/finish", dependencies=[Depends(require_perm("stocktake:order:finish"))])
async def finish_stocktake(order_id: int, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """完成盘点：未盘明细按账面处理，差异明细生成盈亏调整流水并更新库存。"""
    order = (await db.execute(select(StocktakeOrder).where(StocktakeOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("盘点单不存在")
    if order.status != "processing":
        raise bad_request("盘点单不在进行中")
    items = (await db.execute(select(StocktakeItem).where(StocktakeItem.order_id == order_id))).scalars().all()
    if not any(i.actual_qty is not None for i in items):
        raise bad_request("尚未录入任何实盘数量")
    try:
        for i in items:
            if i.actual_qty is None:
                continue  # 未盘按账面，无差异
            diff = float(i.actual_qty) - float(i.book_qty)
            if diff != 0:
                await apply_stock_change(
                    db, goods_id=i.goods_id, warehouse_id=order.warehouse_id, location_id=i.location_id,
                    qty_change=diff, biz_type="stocktake", order_no=order.order_no,
                    operator_id=current.id, operator_name=current.nickname or current.username,
                )
        order.status = "finished"
        order.finished_at = datetime.now()
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await get_stocktake(order_id, db)


@router.post("/{order_id}/cancel", dependencies=[Depends(require_perm("stocktake:order:finish"))])
async def cancel_stocktake(order_id: int, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(StocktakeOrder).where(StocktakeOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found()
    if order.status != "processing":
        raise bad_request("仅进行中的盘点单可作废")
    order.status = "cancelled"
    await db.commit()
    return await _detail(db, order)
