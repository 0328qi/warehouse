from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import bad_request, not_found, paginate, soft_delete
from app.core.database import get_db
from app.core.deps import get_current_user, get_warehouse_scope, require_perm
from app.models import (
    Customer,
    Goods,
    GoodsCategory,
    Inventory,
    Location,
    Supplier,
    SysUser,
    Warehouse,
    Zone,
)
from app.schemas.basic import (
    CategoryCreate,
    CategoryUpdate,
    GoodsCreate,
    GoodsUpdate,
    LocationBatchCreate,
    LocationCreate,
    LocationUpdate,
    PartnerCreate,
    PartnerUpdate,
    WarehouseCreate,
    WarehouseUpdate,
    ZoneCreate,
    ZoneUpdate,
)

router = APIRouter(prefix="/basic", tags=["基础数据"])


async def gen_code(db: AsyncSession, model, prefix: str) -> str:
    result = await db.execute(select(func.count()).select_from(model).where(model.is_deleted.is_(False)))
    count = result.scalar_one()
    return f"{prefix}{count + 1:04d}"


def apply_warehouse_scope(stmt, model, scope: list[int] | None):
    if scope is None:
        return stmt
    if not scope:
        return stmt.where(model.warehouse_id.in_([-1]))
    return stmt.where(model.warehouse_id.in_(scope))


# ============ 仓库 ============
@router.get("/warehouses", dependencies=[Depends(require_perm("basic:warehouse:list"))])
async def list_warehouses(
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Warehouse).where(Warehouse.is_deleted.is_(False)).order_by(Warehouse.id)
    if keyword:
        stmt = stmt.where(Warehouse.code.contains(keyword) | Warehouse.name.contains(keyword))
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.get("/warehouses/all", dependencies=[Depends(get_current_user)])
async def all_warehouses(db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    """下拉框用：按数据权限过滤。"""
    stmt = select(Warehouse).where(Warehouse.is_deleted.is_(False), Warehouse.status.is_(True)).order_by(Warehouse.id)
    scope = get_warehouse_scope(current)
    stmt = apply_warehouse_scope(stmt, Warehouse, scope)
    warehouses = (await db.execute(stmt)).scalars().all()
    return [{"id": w.id, "code": w.code, "name": w.name} for w in warehouses]


@router.post("/warehouses", dependencies=[Depends(require_perm("basic:warehouse:create"))])
async def create_warehouse(body: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Warehouse).where(Warehouse.code == body.code, Warehouse.is_deleted.is_(False)))
    if exists.scalar_one_or_none():
        raise bad_request("仓库编码已存在")
    wh = Warehouse(**body.model_dump())
    db.add(wh)
    await db.commit()
    return wh


@router.put("/warehouses/{wid}", dependencies=[Depends(require_perm("basic:warehouse:update"))])
async def update_warehouse(wid: int, body: WarehouseUpdate, db: AsyncSession = Depends(get_db)):
    wh = await db.get(Warehouse, wid)
    if not wh or wh.is_deleted:
        raise not_found("仓库不存在")
    for k, v in body.model_dump().items():
        setattr(wh, k, v)
    await db.commit()
    return wh


@router.delete("/warehouses/{wid}", dependencies=[Depends(require_perm("basic:warehouse:delete"))])
async def delete_warehouse(wid: int, db: AsyncSession = Depends(get_db)):
    has_stock = (
        await db.execute(select(func.count()).select_from(Inventory).where(Inventory.warehouse_id == wid))
    ).scalar_one()
    if has_stock > 0:
        raise bad_request("仓库下仍有库存，不能删除")
    wh = await db.get(Warehouse, wid)
    if not wh:
        raise not_found()
    await soft_delete(db, wh)
    return {"message": "ok"}


# ============ 库区 ============
@router.get("/zones", dependencies=[Depends(require_perm("basic:zone:list"))])
async def list_zones(
    warehouse_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Zone).where(Zone.is_deleted.is_(False)).order_by(Zone.id)
    if warehouse_id:
        stmt = stmt.where(Zone.warehouse_id == warehouse_id)
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.get("/zones/all", dependencies=[Depends(get_current_user)])
async def all_zones(warehouse_id: int, db: AsyncSession = Depends(get_db)):
    zones = (
        await db.execute(select(Zone).where(Zone.warehouse_id == warehouse_id, Zone.is_deleted.is_(False)))
    ).scalars().all()
    return [{"id": z.id, "code": z.code, "name": z.name, "type": z.type} for z in zones]


@router.post("/zones", dependencies=[Depends(require_perm("basic:zone:create"))])
async def create_zone(body: ZoneCreate, db: AsyncSession = Depends(get_db)):
    wh = await db.get(Warehouse, body.warehouse_id)
    if not wh or wh.is_deleted:
        raise bad_request("仓库不存在")
    zone = Zone(**body.model_dump())
    db.add(zone)
    await db.commit()
    return zone


@router.put("/zones/{zid}", dependencies=[Depends(require_perm("basic:zone:update"))])
async def update_zone(zid: int, body: ZoneUpdate, db: AsyncSession = Depends(get_db)):
    zone = await db.get(Zone, zid)
    if not zone or zone.is_deleted:
        raise not_found()
    for k, v in body.model_dump().items():
        setattr(zone, k, v)
    await db.commit()
    return zone


@router.delete("/zones/{zid}", dependencies=[Depends(require_perm("basic:zone:delete"))])
async def delete_zone(zid: int, db: AsyncSession = Depends(get_db)):
    has_loc = (await db.execute(select(func.count()).select_from(Location).where(Location.zone_id == zid))).scalar_one()
    if has_loc > 0:
        raise bad_request("库区下仍有库位，不能删除")
    zone = await db.get(Zone, zid)
    if not zone:
        raise not_found()
    await soft_delete(db, zone)
    return {"message": "ok"}


# ============ 库位 ============
@router.get("/locations", dependencies=[Depends(require_perm("basic:location:list"))])
async def list_locations(
    warehouse_id: int | None = None,
    zone_id: int | None = None,
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Location).where(Location.is_deleted.is_(False)).order_by(Location.code)
    if warehouse_id:
        stmt = stmt.where(Location.warehouse_id == warehouse_id)
    if zone_id:
        stmt = stmt.where(Location.zone_id == zone_id)
    if keyword:
        stmt = stmt.where(Location.code.contains(keyword))
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.get("/locations/all", dependencies=[Depends(get_current_user)])
async def all_locations(
    zone_id: int | None = None,
    warehouse_id: int | None = None,
    keyword: str = "",
    db: AsyncSession = Depends(get_db),
):
    """下拉/扫码定位用，最多返回 200 条。"""
    stmt = select(Location).where(Location.is_deleted.is_(False), Location.status.is_(True)).order_by(Location.code).limit(200)
    if zone_id:
        stmt = stmt.where(Location.zone_id == zone_id)
    if warehouse_id:
        stmt = stmt.where(Location.warehouse_id == warehouse_id)
    if keyword:
        stmt = stmt.where(Location.code.contains(keyword))
    locations = (await db.execute(stmt)).scalars().all()
    return [{"id": l.id, "code": l.code, "warehouse_id": l.warehouse_id, "zone_id": l.zone_id} for l in locations]


@router.post("/locations", dependencies=[Depends(require_perm("basic:location:create"))])
async def create_location(body: LocationCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Location).where(Location.code == body.code, Location.is_deleted.is_(False)))
    if exists.scalar_one_or_none():
        raise bad_request("库位编码已存在")
    loc = Location(**body.model_dump())
    db.add(loc)
    await db.commit()
    return loc


@router.post("/locations/batch", dependencies=[Depends(require_perm("basic:location:create"))])
async def batch_create_locations(body: LocationBatchCreate, db: AsyncSession = Depends(get_db)):
    """批量生成库位：{前缀}-行-列，如 A-01-01。"""
    if body.rows < 1 or body.cols < 1 or body.rows * body.cols > 1000:
        raise bad_request("行列数量不合法（单批最多 1000 个）")
    existing = {
        code
        for (code,) in (
            await db.execute(select(Location.code).where(Location.is_deleted.is_(False)))
        ).all()
    }
    created = []
    for r in range(1, body.rows + 1):
        for c in range(1, body.cols + 1):
            code = f"{body.prefix}-{r:02d}-{c:02d}"
            if code in existing:
                continue
            db.add(Location(warehouse_id=body.warehouse_id, zone_id=body.zone_id, code=code))
            created.append(code)
    await db.commit()
    return {"message": f"已创建 {len(created)} 个库位", "codes": created}


@router.put("/locations/{lid}", dependencies=[Depends(require_perm("basic:location:update"))])
async def update_location(lid: int, body: LocationUpdate, db: AsyncSession = Depends(get_db)):
    loc = await db.get(Location, lid)
    if not loc or loc.is_deleted:
        raise not_found()
    loc.status = body.status
    loc.remark = body.remark
    await db.commit()
    return loc


@router.delete("/locations/{lid}", dependencies=[Depends(require_perm("basic:location:delete"))])
async def delete_location(lid: int, db: AsyncSession = Depends(get_db)):
    has_stock = (
        await db.execute(select(func.count()).select_from(Inventory).where(Inventory.location_id == lid))
    ).scalar_one()
    if has_stock > 0:
        raise bad_request("库位上仍有库存，不能删除")
    loc = await db.get(Location, lid)
    if not loc:
        raise not_found()
    await soft_delete(db, loc)
    return {"message": "ok"}


# ============ 商品分类 ============
@router.get("/goods-categories/tree", dependencies=[Depends(get_current_user)])
async def category_tree(db: AsyncSession = Depends(get_db)):
    cats = (
        await db.execute(select(GoodsCategory).where(GoodsCategory.is_deleted.is_(False)).order_by(GoodsCategory.sort))
    ).scalars().all()

    def build(parent_id: int) -> list[dict]:
        nodes = []
        for c in cats:
            if c.parent_id == parent_id:
                node = {"id": c.id, "parent_id": c.parent_id, "name": c.name, "sort": c.sort}
                node["children"] = build(c.id)
                nodes.append(node)
        return nodes

    return build(0)


@router.post("/goods-categories", dependencies=[Depends(require_perm("basic:goods:create"))])
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    cat = GoodsCategory(**body.model_dump())
    db.add(cat)
    await db.commit()
    return {"id": cat.id, "name": cat.name}


@router.put("/goods-categories/{cid}", dependencies=[Depends(require_perm("basic:goods:update"))])
async def update_category(cid: int, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await db.get(GoodsCategory, cid)
    if not cat or cat.is_deleted:
        raise not_found()
    cat.name = body.name or cat.name
    cat.sort = body.sort
    await db.commit()
    return {"message": "ok"}


@router.delete("/goods-categories/{cid}", dependencies=[Depends(require_perm("basic:goods:delete"))])
async def delete_category(cid: int, db: AsyncSession = Depends(get_db)):
    has_goods = (await db.execute(select(func.count()).select_from(Goods).where(Goods.category_id == cid, Goods.is_deleted.is_(False)))).scalar_one()
    has_child = (await db.execute(select(func.count()).select_from(GoodsCategory).where(GoodsCategory.parent_id == cid, GoodsCategory.is_deleted.is_(False)))).scalar_one()
    if has_goods or has_child:
        raise bad_request("分类下仍有商品或子分类，不能删除")
    cat = await db.get(GoodsCategory, cid)
    if not cat:
        raise not_found()
    await soft_delete(db, cat)
    return {"message": "ok"}


# ============ 商品 ============
@router.get("/goods", dependencies=[Depends(require_perm("basic:goods:list"))])
async def list_goods(
    keyword: str = "",
    category_id: int | None = None,
    status: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Goods).where(Goods.is_deleted.is_(False)).order_by(Goods.id.desc())
    if keyword:
        stmt = stmt.where(Goods.code.contains(keyword) | Goods.name.contains(keyword) | Goods.barcode.contains(keyword))
    if category_id:
        stmt = stmt.where(Goods.category_id == category_id)
    if status is not None:
        stmt = stmt.where(Goods.status == status)
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.post("/goods", dependencies=[Depends(require_perm("basic:goods:create"))])
async def create_goods(body: GoodsCreate, db: AsyncSession = Depends(get_db)):
    code = await gen_code(db, Goods, "SKU")
    goods = Goods(code=code, **body.model_dump())
    db.add(goods)
    await db.commit()
    return goods


@router.put("/goods/{gid}", dependencies=[Depends(require_perm("basic:goods:update"))])
async def update_goods(gid: int, body: GoodsUpdate, db: AsyncSession = Depends(get_db)):
    goods = await db.get(Goods, gid)
    if not goods or goods.is_deleted:
        raise not_found("商品不存在")
    data = body.model_dump()
    for k, v in data.items():
        setattr(goods, k, v)
    await db.commit()
    return goods


@router.delete("/goods/{gid}", dependencies=[Depends(require_perm("basic:goods:delete"))])
async def delete_goods(gid: int, db: AsyncSession = Depends(get_db)):
    has_stock = (
        await db.execute(select(func.sum(Inventory.qty)).where(Inventory.goods_id == gid))
    ).scalar_one()
    if has_stock:
        raise bad_request("商品仍有库存，不能删除")
    goods = await db.get(Goods, gid)
    if not goods:
        raise not_found()
    await soft_delete(db, goods)
    return {"message": "ok"}


# ============ 供应商 ============
@router.get("/suppliers", dependencies=[Depends(require_perm("basic:supplier:list"))])
async def list_suppliers(
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Supplier).where(Supplier.is_deleted.is_(False)).order_by(Supplier.id.desc())
    if keyword:
        stmt = stmt.where(Supplier.code.contains(keyword) | Supplier.name.contains(keyword))
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.get("/suppliers/all", dependencies=[Depends(get_current_user)])
async def all_suppliers(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Supplier).where(Supplier.is_deleted.is_(False)).order_by(Supplier.id))).scalars().all()
    return [{"id": s.id, "code": s.code, "name": s.name} for s in rows]


@router.post("/suppliers", dependencies=[Depends(require_perm("basic:supplier:create"))])
async def create_supplier(body: PartnerCreate, db: AsyncSession = Depends(get_db)):
    code = await gen_code(db, Supplier, "SUP")
    supplier = Supplier(code=code, **body.model_dump())
    db.add(supplier)
    await db.commit()
    return supplier


@router.put("/suppliers/{sid}", dependencies=[Depends(require_perm("basic:supplier:update"))])
async def update_supplier(sid: int, body: PartnerUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Supplier, sid)
    if not obj or obj.is_deleted:
        raise not_found()
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    return obj


@router.delete("/suppliers/{sid}", dependencies=[Depends(require_perm("basic:supplier:delete"))])
async def delete_supplier(sid: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Supplier, sid)
    if not obj:
        raise not_found()
    await soft_delete(db, obj)
    return {"message": "ok"}


# ============ 客户 ============
@router.get("/customers", dependencies=[Depends(require_perm("basic:customer:list"))])
async def list_customers(
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(Customer).where(Customer.is_deleted.is_(False)).order_by(Customer.id.desc())
    if keyword:
        stmt = stmt.where(Customer.code.contains(keyword) | Customer.name.contains(keyword))
    total, items = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": items}


@router.get("/customers/all", dependencies=[Depends(get_current_user)])
async def all_customers(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Customer).where(Customer.is_deleted.is_(False)).order_by(Customer.id))).scalars().all()
    return [{"id": c.id, "code": c.code, "name": c.name} for c in rows]


@router.post("/customers", dependencies=[Depends(require_perm("basic:customer:create"))])
async def create_customer(body: PartnerCreate, db: AsyncSession = Depends(get_db)):
    code = await gen_code(db, Customer, "CUS")
    customer = Customer(code=code, **body.model_dump())
    db.add(customer)
    await db.commit()
    return customer


@router.put("/customers/{cid}", dependencies=[Depends(require_perm("basic:customer:update"))])
async def update_customer(cid: int, body: PartnerUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Customer, cid)
    if not obj or obj.is_deleted:
        raise not_found()
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    return obj


@router.delete("/customers/{cid}", dependencies=[Depends(require_perm("basic:customer:delete"))])
async def delete_customer(cid: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Customer, cid)
    if not obj:
        raise not_found()
    await soft_delete(db, obj)
    return {"message": "ok"}
