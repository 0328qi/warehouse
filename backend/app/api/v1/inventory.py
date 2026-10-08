from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import bad_request, paginate
from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import Goods, Inventory, InventoryTransaction, Location, SysUser, Warehouse
from app.schemas.basic import MoveIn
from app.services.inventory import apply_stock_change, generate_order_no

router = APIRouter(prefix="/inventory", tags=["库存管理"])


def apply_scope(stmt, model, scope):
    if scope is None:
        return stmt
    if not scope:
        return stmt.where(model.warehouse_id.in_([-1]))
    return stmt.where(model.warehouse_id.in_(scope))


@router.get("/balances", dependencies=[Depends(require_perm("inventory:balance:list"))])
async def list_balances(
    keyword: str = "",
    warehouse_id: int | None = None,
    location_id: int | None = None,
    goods_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = (
        select(
            Inventory,
            Goods.name.label("goods_name"),
            Goods.code.label("goods_code"),
            Goods.unit.label("unit"),
            Warehouse.name.label("warehouse_name"),
            Location.code.label("location_code"),
        )
        .join(Goods, Inventory.goods_id == Goods.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Location, Inventory.location_id == Location.id)
        .order_by(Inventory.id)
    )
    stmt = apply_scope(stmt, Inventory, get_warehouse_scope(current))
    if keyword:
        stmt = stmt.where(Goods.name.contains(keyword) | Goods.code.contains(keyword))
    if warehouse_id:
        stmt = stmt.where(Inventory.warehouse_id == warehouse_id)
    if location_id:
        stmt = stmt.where(Inventory.location_id == location_id)
    if goods_id:
        stmt = stmt.where(Inventory.goods_id == goods_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt.limit(page_size).offset((page - 1) * page_size))).all()
    items = [
        {
            "id": inv.id,
            "goods_id": inv.goods_id,
            "warehouse_id": inv.warehouse_id,
            "location_id": inv.location_id,
            "qty": float(inv.qty),
            "goods_name": goods_name,
            "goods_code": goods_code,
            "unit": unit,
            "warehouse_name": warehouse_name,
            "location_code": location_code,
        }
        for inv, goods_name, goods_code, unit, warehouse_name, location_code in rows
    ]
    return {"total": total, "items": items}


@router.get("/transactions", dependencies=[Depends(require_perm("inventory:transaction:list"))])
async def list_transactions(
    order_no: str = "",
    biz_type: str | None = None,
    warehouse_id: int | None = None,
    goods_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    stmt = (
        select(
            InventoryTransaction,
            Goods.name.label("goods_name"),
            Warehouse.name.label("warehouse_name"),
            Location.code.label("location_code"),
        )
        .join(Goods, InventoryTransaction.goods_id == Goods.id)
        .join(Warehouse, InventoryTransaction.warehouse_id == Warehouse.id)
        .join(Location, InventoryTransaction.location_id == Location.id)
        .order_by(InventoryTransaction.id.desc())
    )
    stmt = apply_scope(stmt, InventoryTransaction, get_warehouse_scope(current))
    if order_no:
        stmt = stmt.where(InventoryTransaction.order_no.contains(order_no))
    if biz_type:
        stmt = stmt.where(InventoryTransaction.biz_type == biz_type)
    if warehouse_id:
        stmt = stmt.where(InventoryTransaction.warehouse_id == warehouse_id)
    if goods_id:
        stmt = stmt.where(InventoryTransaction.goods_id == goods_id)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.limit(page_size).offset((page - 1) * page_size))).all()
    items = [
        {
            "id": t.id,
            "order_no": t.order_no,
            "biz_type": t.biz_type,
            "goods_id": t.goods_id,
            "warehouse_id": t.warehouse_id,
            "location_id": t.location_id,
            "qty": float(t.qty),
            "before_qty": float(t.before_qty),
            "after_qty": float(t.after_qty),
            "operator_name": t.operator_name,
            "created_at": t.created_at,
            "goods_name": goods_name,
            "warehouse_name": warehouse_name,
            "location_code": location_code,
        }
        for t, goods_name, warehouse_name, location_code in rows
    ]
    return {"total": total, "items": items}


@router.post("/move", dependencies=[Depends(require_perm("inventory:move"))])
async def move_stock(body: MoveIn, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """库位间移库：同仓库内从源库位扣、目标库位加。"""
    if body.qty <= 0:
        raise bad_request("数量必须大于 0")
    from_loc = await db.get(Location, body.from_location_id)
    to_loc = await db.get(Location, body.to_location_id)
    if not from_loc or not to_loc:
        raise bad_request("库位不存在")
    if from_loc.warehouse_id != to_loc.warehouse_id:
        raise bad_request("跨仓库请使用调拨功能")
    if from_loc.id == to_loc.id:
        raise bad_request("源库位与目标库位相同")
    order_no = await generate_order_no(db, "MV")
    try:
        await apply_stock_change(
            db, goods_id=body.goods_id, warehouse_id=from_loc.warehouse_id, location_id=from_loc.id,
            qty_change=-body.qty, biz_type="move", order_no=order_no,
            operator_id=current.id, operator_name=current.nickname or current.username,
        )
        await apply_stock_change(
            db, goods_id=body.goods_id, warehouse_id=to_loc.warehouse_id, location_id=to_loc.id,
            qty_change=body.qty, biz_type="move", order_no=order_no,
            operator_id=current.id, operator_name=current.nickname or current.username,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {"message": "ok", "order_no": order_no}


@router.get("/warnings", dependencies=[Depends(require_perm("inventory:balance:list"))])
async def stock_warnings(
    warehouse_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current: SysUser = Depends(get_current_user),
):
    """库存上下限预警：按商品汇总库存与 min/max 比较。"""
    stmt = (
        select(
            Goods,
            func.coalesce(func.sum(Inventory.qty), 0).label("total_qty"),
        )
        .outerjoin(Inventory, Inventory.goods_id == Goods.id)
        .where(Goods.is_deleted.is_(False))
        .group_by(Goods.id)
    )
    if warehouse_id:
        # 指定仓库时只汇总该仓库存量，但仍统计全部商品缺货情况意义不大，这里按仓过滤
        stmt = (
            select(Goods, func.coalesce(func.sum(Inventory.qty), 0).label("total_qty"))
            .select_from(Goods)
            .outerjoin(Inventory, (Inventory.goods_id == Goods.id) & (Inventory.warehouse_id == warehouse_id))
            .group_by(Goods.id)
        )
    rows = (await db.execute(stmt)).all()
    warnings = []
    for goods, total_qty in rows:
        total_qty = float(total_qty)
        min_s, max_s = float(goods.min_stock), float(goods.max_stock)
        if min_s > 0 and total_qty < min_s:
            warnings.append({"goods_id": goods.id, "code": goods.code, "name": goods.name, "unit": goods.unit,
                             "total_qty": total_qty, "type": "low", "threshold": min_s})
        elif max_s > 0 and total_qty > max_s:
            warnings.append({"goods_id": goods.id, "code": goods.code, "name": goods.name, "unit": goods.unit,
                             "total_qty": total_qty, "type": "high", "threshold": max_s})
    return {"total": len(warnings), "items": warnings}
