from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import bad_request, not_found, paginate
from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import (
    STATUS_CANCELLED,
    STATUS_DRAFT,
    STATUS_EXECUTED,
    Customer,
    Goods,
    InboundItem,
    InboundOrder,
    Location,
    OutboundItem,
    OutboundOrder,
    Supplier,
    SysUser,
    Warehouse,
)
from app.schemas.order import (
    InboundCreate,
    InboundUpdate,
    OrderOut,
    OutboundCreate,
    OutboundUpdate,
)
from app.services.inventory import apply_stock_change, generate_order_no

router = APIRouter(tags=["出入库"])

IN_TYPES = {"purchase": "purchase_in", "return": "return_in", "other": "other_in"}
OUT_TYPES = {"sale": "sale_out", "use": "use_out", "other": "other_out"}


async def _load_order(db: AsyncSession, model, item_model, order_id: int):
    order = (await db.execute(select(model).where(model.id == order_id))).scalar_one_or_none()
    if not order:
        raise not_found("单据不存在")
    items = (
        (await db.execute(select(item_model).where(item_model.order_id == order_id))).scalars().all()
    )
    return order, items


async def _validate_items(db: AsyncSession, model_cls, warehouse_id: int, items):
    """校验商品/库位有效且库位属于该仓库，并汇总总数。"""
    if not items:
        raise bad_request("单据明细不能为空")
    goods_ids = list({i.goods_id for i in items})
    loc_ids = list({i.location_id for i in items})
    goods_list = (await db.execute(select(Goods).where(Goods.id.in_(goods_ids), Goods.is_deleted.is_(False)))).scalars().all()
    loc_list = (await db.execute(select(Location).where(Location.id.in_(loc_ids), Location.is_deleted.is_(False)))).scalars().all()
    goods_map = {g.id: g for g in goods_list}
    loc_map = {l.id: l for l in loc_list}
    for i in items:
        if i.goods_id not in goods_map:
            raise bad_request(f"商品不存在：{i.goods_id}")
        loc = loc_map.get(i.location_id)
        if loc is None:
            raise bad_request(f"库位不存在：{i.location_id}")
        if loc.warehouse_id != warehouse_id:
            raise bad_request(f"库位 {loc.code} 不属于该仓库")
    total = sum(i.qty for i in items)
    if total <= 0 or any(i.qty <= 0 for i in items):
        raise bad_request("数量必须大于 0")
    return total


def _order_to_dict(order, items, goods_map, loc_map, warehouse_name, partner_name) -> dict:
    data = OrderOut.model_validate(order).model_dump()
    data["warehouse_name"] = warehouse_name
    if hasattr(order, "supplier_id"):
        data["supplier_name"] = partner_name
    else:
        data["customer_name"] = partner_name
    item_out = []
    for i in items:
        g = goods_map.get(i.goods_id)
        l = loc_map.get(i.location_id)
        item_out.append(
            {
                "id": i.id,
                "goods_id": i.goods_id,
                "location_id": i.location_id,
                "qty": float(i.qty),
                "remark": i.remark,
                "goods_name": g.name if g else "",
                "goods_code": g.code if g else "",
                "location_code": l.code if l else "",
            }
        )
    data["items"] = item_out
    return data


async def _detail(db: AsyncSession, order, items) -> dict:
    warehouse = await db.get(Warehouse, order.warehouse_id)
    goods_ids = {i.goods_id for i in items} or {0}
    loc_ids = {i.location_id for i in items} or {0}
    goods_map = {g.id: g for g in (await db.execute(select(Goods).where(Goods.id.in_(goods_ids)))).scalars().all()}
    loc_map = {l.id: l for l in (await db.execute(select(Location).where(Location.id.in_(loc_ids)))).scalars().all()}
    partner_name = ""
    if isinstance(order, InboundOrder) and order.supplier_id:
        sup = await db.get(Supplier, order.supplier_id)
        partner_name = sup.name if sup else ""
    elif isinstance(order, OutboundOrder) and order.customer_id:
        cus = await db.get(Customer, order.customer_id)
        partner_name = cus.name if cus else ""
    return _order_to_dict(order, items, goods_map, loc_map, warehouse.name if warehouse else "", partner_name)


# ================= 入库 =================
inbound_router = APIRouter(prefix="/inbound/orders", dependencies=[Depends(require_perm("inbound:order:list"))])


@inbound_router.get("")
async def list_inbound(
    keyword: str = "",
    status: str | None = None,
    type: str | None = None,
    warehouse_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = select(InboundOrder).order_by(InboundOrder.id.desc())
    stmt = apply_scope(stmt, InboundOrder, get_warehouse_scope(current))
    if keyword:
        stmt = stmt.where(InboundOrder.order_no.contains(keyword))
    if status:
        stmt = stmt.where(InboundOrder.status == status)
    if type:
        stmt = stmt.where(InboundOrder.type == type)
    if warehouse_id:
        stmt = stmt.where(InboundOrder.warehouse_id == warehouse_id)
    total, orders = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": [await _detail(db, o, []) for o in orders]}


def apply_scope(stmt, model, scope):
    if scope is None:
        return stmt
    if not scope:
        return stmt.where(model.warehouse_id.in_([-1]))
    return stmt.where(model.warehouse_id.in_(scope))


@inbound_router.get("/{order_id}")
async def get_inbound(order_id: int, db: AsyncSession = Depends(get_db)):
    order, items = await _load_order(db, InboundOrder, InboundItem, order_id)
    return await _detail(db, order, items)


@inbound_router.post("", dependencies=[Depends(require_perm("inbound:order:create"))])
async def create_inbound(body: InboundCreate, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    if body.type not in IN_TYPES:
        raise bad_request("入库类型不合法")
    await _validate_items(db, InboundItem, body.warehouse_id, body.items)
    order_no = await generate_order_no(db, "IN")
    order = InboundOrder(
        order_no=order_no,
        type=body.type,
        warehouse_id=body.warehouse_id,
        supplier_id=body.supplier_id,
        status=STATUS_DRAFT,
        total_qty=sum(i.qty for i in body.items),
        remark=body.remark,
        creator_id=current.id,
        creator_name=current.nickname or current.username,
    )
    db.add(order)
    await db.flush()
    for i in body.items:
        db.add(InboundItem(order_id=order.id, **i.model_dump()))
    await db.commit()
    return await get_inbound(order.id, db)


@inbound_router.put("/{order_id}", dependencies=[Depends(require_perm("inbound:order:update"))])
async def update_inbound(order_id: int, body: InboundUpdate, db: AsyncSession = Depends(get_db)):
    order, _ = await _load_order(db, InboundOrder, InboundItem, order_id)
    if order.status != STATUS_DRAFT:
        raise bad_request("仅草稿状态可编辑")
    if body.type and body.type not in IN_TYPES:
        raise bad_request("入库类型不合法")
    await _validate_items(db, InboundItem, order.warehouse_id, body.items)
    order.type = body.type or order.type
    order.supplier_id = body.supplier_id
    order.remark = body.remark
    order.total_qty = sum(i.qty for i in body.items)
    await db.execute(InboundItem.__table__.delete().where(InboundItem.order_id == order_id))
    for i in body.items:
        db.add(InboundItem(order_id=order_id, **i.model_dump()))
    await db.commit()
    return await get_inbound(order_id, db)


@inbound_router.post("/{order_id}/execute", dependencies=[Depends(require_perm("inbound:order:execute"))])
async def execute_inbound(order_id: int, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """执行入库：库存增加。一步执行模式下保存+执行也可连续调用。"""
    order, items = await _load_order(db, InboundOrder, InboundItem, order_id)
    if order.status != STATUS_DRAFT:
        raise bad_request("仅草稿状态可执行")
    try:
        for i in items:
            await apply_stock_change(
                db,
                goods_id=i.goods_id,
                warehouse_id=order.warehouse_id,
                location_id=i.location_id,
                qty_change=float(i.qty),
                biz_type=IN_TYPES[order.type],
                order_no=order.order_no,
                operator_id=current.id,
                operator_name=current.nickname or current.username,
            )
        order.status = STATUS_EXECUTED
        order.executed_at = datetime.now()
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await get_inbound(order_id, db)


@inbound_router.post("/{order_id}/cancel", dependencies=[Depends(require_perm("inbound:order:cancel"))])
async def cancel_inbound(order_id: int, db: AsyncSession = Depends(get_db)):
    order, _ = await _load_order(db, InboundOrder, InboundItem, order_id)
    if order.status == STATUS_EXECUTED:
        raise bad_request("已执行单据不可作废")
    if order.status == STATUS_CANCELLED:
        raise bad_request("单据已作废")
    order.status = STATUS_CANCELLED
    await db.commit()
    return await get_inbound(order_id, db)


# ================= 出库 =================
outbound_router = APIRouter(prefix="/outbound/orders", dependencies=[Depends(require_perm("outbound:order:list"))])


@outbound_router.get("")
async def list_outbound(
    keyword: str = "",
    status: str | None = None,
    type: str | None = None,
    warehouse_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = select(OutboundOrder).order_by(OutboundOrder.id.desc())
    stmt = apply_scope(stmt, OutboundOrder, get_warehouse_scope(current))
    if keyword:
        stmt = stmt.where(OutboundOrder.order_no.contains(keyword))
    if status:
        stmt = stmt.where(OutboundOrder.status == status)
    if type:
        stmt = stmt.where(OutboundOrder.type == type)
    if warehouse_id:
        stmt = stmt.where(OutboundOrder.warehouse_id == warehouse_id)
    total, orders = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": [await _detail(db, o, []) for o in orders]}


@outbound_router.get("/{order_id}")
async def get_outbound(order_id: int, db: AsyncSession = Depends(get_db)):
    order, items = await _load_order(db, OutboundOrder, OutboundItem, order_id)
    return await _detail(db, order, items)


@outbound_router.post("", dependencies=[Depends(require_perm("outbound:order:create"))])
async def create_outbound(body: OutboundCreate, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    if body.type not in OUT_TYPES:
        raise bad_request("出库类型不合法")
    await _validate_items(db, OutboundItem, body.warehouse_id, body.items)
    order_no = await generate_order_no(db, "OUT")
    order = OutboundOrder(
        order_no=order_no,
        type=body.type,
        warehouse_id=body.warehouse_id,
        customer_id=body.customer_id,
        status=STATUS_DRAFT,
        total_qty=sum(i.qty for i in body.items),
        remark=body.remark,
        creator_id=current.id,
        creator_name=current.nickname or current.username,
    )
    db.add(order)
    await db.flush()
    for i in body.items:
        db.add(OutboundItem(order_id=order.id, goods_id=i.goods_id, location_id=i.location_id, qty=i.qty, remark=i.remark))
    await db.commit()
    return await get_outbound(order.id, db)


@outbound_router.put("/{order_id}", dependencies=[Depends(require_perm("outbound:order:update"))])
async def update_outbound(order_id: int, body: OutboundUpdate, db: AsyncSession = Depends(get_db)):
    order, _ = await _load_order(db, OutboundOrder, OutboundItem, order_id)
    if order.status != STATUS_DRAFT:
        raise bad_request("仅草稿状态可编辑")
    if body.type and body.type not in OUT_TYPES:
        raise bad_request("出库类型不合法")
    await _validate_items(db, OutboundItem, order.warehouse_id, body.items)
    order.type = body.type or order.type
    order.customer_id = body.customer_id
    order.remark = body.remark
    order.total_qty = sum(i.qty for i in body.items)
    await db.execute(OutboundItem.__table__.delete().where(OutboundItem.order_id == order_id))
    for i in body.items:
        db.add(OutboundItem(order_id=order_id, goods_id=i.goods_id, location_id=i.location_id, qty=i.qty, remark=i.remark))
    await db.commit()
    return await get_outbound(order_id, db)


@outbound_router.post("/{order_id}/execute", dependencies=[Depends(require_perm("outbound:order:execute"))])
async def execute_outbound(order_id: int, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """执行出库：库存扣减（行锁防超扣）。"""
    order, items = await _load_order(db, OutboundOrder, OutboundItem, order_id)
    if order.status != STATUS_DRAFT:
        raise bad_request("仅草稿状态可执行")
    try:
        for i in items:
            await apply_stock_change(
                db,
                goods_id=i.goods_id,
                warehouse_id=order.warehouse_id,
                location_id=i.location_id,
                qty_change=-float(i.qty),
                biz_type=OUT_TYPES[order.type],
                order_no=order.order_no,
                operator_id=current.id,
                operator_name=current.nickname or current.username,
            )
        order.status = STATUS_EXECUTED
        order.executed_at = datetime.now()
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await get_outbound(order_id, db)


@outbound_router.post("/{order_id}/cancel", dependencies=[Depends(require_perm("outbound:order:cancel"))])
async def cancel_outbound(order_id: int, db: AsyncSession = Depends(get_db)):
    order, _ = await _load_order(db, OutboundOrder, OutboundItem, order_id)
    if order.status == STATUS_EXECUTED:
        raise bad_request("已执行单据不可作废")
    if order.status == STATUS_CANCELLED:
        raise bad_request("单据已作废")
    order.status = STATUS_CANCELLED
    await db.commit()
    return await get_outbound(order_id, db)


router.include_router(inbound_router)
router.include_router(outbound_router)
