from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope
from app.models import Goods, Inventory, InventoryTransaction, StocktakeOrder, SysUser

router = APIRouter(prefix="/dashboard", tags=["看板"])


@router.get("/stats", dependencies=[Depends(get_current_user)])
async def stats(db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    scope = get_warehouse_scope(current)

    total_qty_stmt = select(func.coalesce(func.sum(Inventory.qty), 0), func.count(Inventory.id))
    if scope is not None:
        total_qty_stmt = total_qty_stmt.where(Inventory.warehouse_id.in_(scope or [-1]))
    total_qty, sku_locations = (await db.execute(total_qty_stmt)).one()

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    in_qty_stmt = select(func.coalesce(func.sum(func.abs(InventoryTransaction.qty)), 0)).where(
        InventoryTransaction.qty > 0, InventoryTransaction.created_at >= today_start
    )
    out_qty_stmt = select(func.coalesce(func.sum(func.abs(InventoryTransaction.qty)), 0)).where(
        InventoryTransaction.qty < 0, InventoryTransaction.created_at >= today_start
    )
    if scope is not None:
        in_qty_stmt = in_qty_stmt.where(InventoryTransaction.warehouse_id.in_(scope or [-1]))
        out_qty_stmt = out_qty_stmt.where(InventoryTransaction.warehouse_id.in_(scope or [-1]))
    today_in = (await db.execute(in_qty_stmt)).scalar_one()
    today_out = (await db.execute(out_qty_stmt)).scalar_one()

    goods_count = (await db.execute(select(func.count()).select_from(Goods).where(Goods.is_deleted.is_(False)))).scalar_one()

    # 预警数：低于下限的商品
    warn_stmt = (
        select(func.count())
        .select_from(
            select(Goods.id, func.coalesce(func.sum(Inventory.qty), 0).label("t"))
            .outerjoin(Inventory, Inventory.goods_id == Goods.id)
            .where(Goods.is_deleted.is_(False), Goods.min_stock > 0)
            .group_by(Goods.id)
            .having(func.coalesce(func.sum(Inventory.qty), 0) < Goods.min_stock)
            .subquery()
        )
    )
    warn_count = (await db.execute(warn_stmt)).scalar_one()

    # 近 7 天出入库趋势：入/出分开聚合，避免 PG 表达式分组问题
    week_ago = today_start - timedelta(days=6)

    def trend_stmt(direction: str):
        q = select(
            func.date(InventoryTransaction.created_at).label("d"),
            func.sum(func.abs(InventoryTransaction.qty)),
        ).where(InventoryTransaction.created_at >= week_ago)
        if scope is not None:
            q = q.where(InventoryTransaction.warehouse_id.in_(scope or [-1]))
        q = q.where(InventoryTransaction.qty > 0 if direction == "in" else InventoryTransaction.qty < 0)
        return q.group_by(func.date(InventoryTransaction.created_at))

    in_rows = {str(d): float(v or 0) for d, v in (await db.execute(trend_stmt("in"))).all()}
    out_rows = {str(d): float(v or 0) for d, v in (await db.execute(trend_stmt("out"))).all()}
    trend = [
        {
            "date": str((today_start - timedelta(days=i)).date()),
            "in": in_rows.get(str((today_start - timedelta(days=i)).date()), 0),
            "out": out_rows.get(str((today_start - timedelta(days=i)).date()), 0),
        }
        for i in range(6, -1, -1)
    ]

    processing_stocktakes = (
        await db.execute(select(func.count()).select_from(StocktakeOrder).where(StocktakeOrder.status == "processing"))
    ).scalar_one()

    return {
        "total_qty": float(total_qty),
        "sku_locations": sku_locations,
        "goods_count": goods_count,
        "today_in": float(today_in),
        "today_out": float(today_out),
        "warning_count": warn_count,
        "processing_stocktakes": processing_stocktakes,
        "trend": trend,
    }
