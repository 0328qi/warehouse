from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import Goods, Inventory, InventoryTransaction, Location, SysUser, Warehouse

router = APIRouter(prefix="/export", tags=["导出"])


def _xlsx_response(headers: list[str], rows: list[list], filename: str) -> StreamingResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/inventory", dependencies=[Depends(require_perm("inventory:balance:list"))])
async def export_inventory(db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    stmt = (
        select(Goods.code, Goods.name, Goods.unit, Warehouse.name, Location.code, Inventory.qty)
        .join(Goods, Inventory.goods_id == Goods.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Location, Inventory.location_id == Location.id)
        .order_by(Goods.code)
    )
    scope = get_warehouse_scope(current)
    if scope is not None:
        stmt = stmt.where(Inventory.warehouse_id.in_(scope or [-1]))
    rows = (await db.execute(stmt)).all()
    return _xlsx_response(
        ["商品编码", "商品名称", "单位", "仓库", "库位", "库存数量"],
        [[r[0], r[1], r[2], r[3], r[4], float(r[5])] for r in rows],
        "inventory.xlsx",
    )


@router.get("/transactions", dependencies=[Depends(require_perm("inventory:transaction:list"))])
async def export_transactions(db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    stmt = (
        select(
            InventoryTransaction.order_no, InventoryTransaction.biz_type,
            Goods.code, Goods.name, Warehouse.name, Location.code,
            InventoryTransaction.qty, InventoryTransaction.before_qty, InventoryTransaction.after_qty,
            InventoryTransaction.operator_name, InventoryTransaction.created_at,
        )
        .join(Goods, InventoryTransaction.goods_id == Goods.id)
        .join(Warehouse, InventoryTransaction.warehouse_id == Warehouse.id)
        .join(Location, InventoryTransaction.location_id == Location.id)
        .order_by(InventoryTransaction.id.desc())
        .limit(50000)
    )
    scope = get_warehouse_scope(current)
    if scope is not None:
        stmt = stmt.where(InventoryTransaction.warehouse_id.in_(scope or [-1]))
    rows = (await db.execute(stmt)).all()
    return _xlsx_response(
        ["单号", "业务类型", "商品编码", "商品名称", "仓库", "库位", "变动数量", "变动前", "变动后", "操作人", "时间"],
        [[r[0], r[1], r[2], r[3], r[4], r[5], float(r[6]), float(r[7]), float(r[8]), r[9], str(r[10])] for r in rows],
        "transactions.xlsx",
    )
