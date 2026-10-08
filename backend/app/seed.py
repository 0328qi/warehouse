"""初始化种子数据：admin 账号、菜单树、示例仓库/库区/库位。

用法：cd backend && python -m app.seed
"""
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Base,
    GoodsCategory,
    Location,
    SysMenu,
    SysRole,
    SysUser,
    SysUserWarehouse,
    Warehouse,
    Zone,
)

MENUS = [
    # (parent_key, key, name, type, path, component, perm, icon, sort)
    (None, "dashboard", "看板", "menu", "/dashboard", "dashboard/index", "", "Odometer", 1),
    (None, "basic", "基础数据", "dir", "/basic", "", "", "Box", 10),
    ("basic", "basic-warehouse", "仓库管理", "menu", "/basic/warehouse", "basic/warehouse", "basic:warehouse:list", "OfficeBuilding", 1),
    ("basic", "basic-location", "库区库位", "menu", "/basic/location", "basic/location", "basic:location:list", "LocationInformation", 2),
    ("basic", "basic-goods", "商品管理", "menu", "/basic/goods", "basic/goods", "basic:goods:list", "Goods", 3),
    ("basic", "basic-partner", "供应商/客户", "menu", "/basic/partner", "basic/partner", "basic:supplier:list", "User", 4),
    (None, "inbound", "入库管理", "dir", "/inbound", "", "", "Download", 20),
    ("inbound", "inbound-order", "入库单", "menu", "/inbound/order", "inbound/order", "inbound:order:list", "List", 1),
    (None, "outbound", "出库管理", "dir", "/outbound", "", "", "Upload", 30),
    ("outbound", "outbound-order", "出库单", "menu", "/outbound/order", "outbound/order", "outbound:order:list", "List", 1),
    (None, "inventory", "库存管理", "dir", "/inventory", "", "", "Grid", 40),
    ("inventory", "inv-balance", "库存查询", "menu", "/inventory/balance", "inventory/balance", "inventory:balance:list", "DataAnalysis", 1),
    ("inventory", "inv-move", "移库/调拨", "menu", "/inventory/move", "inventory/move", "inventory:move", "Switch", 2),
    ("inventory", "inv-transfer", "调拨单", "menu", "/inventory/transfer", "inventory/transfer", "inventory:transfer:list", "Sort", 3),
    ("inventory", "inv-transaction", "库存流水", "menu", "/inventory/transaction", "inventory/transaction", "inventory:transaction:list", "Document", 4),
    ("inventory", "inv-warning", "库存预警", "menu", "/inventory/warning", "inventory/warning", "inventory:balance:list", "Warning", 5),
    (None, "stocktake", "盘点管理", "dir", "/stocktake", "", "", "Checked", 50),
    ("stocktake", "stocktake-order", "盘点单", "menu", "/stocktake/order", "stocktake/order", "stocktake:order:list", "List", 1),
    (None, "system", "系统管理", "dir", "/system", "", "", "Setting", 90),
    ("system", "sys-user", "用户管理", "menu", "/system/user", "system/user", "system:user:list", "UserFilled", 1),
    ("system", "sys-role", "角色管理", "menu", "/system/role", "system/role", "system:role:list", "Avatar", 2),
    ("system", "sys-menu", "菜单管理", "menu", "/system/menu", "system/menu", "system:menu:list", "Menu", 3),
    # 按钮权限
    ("basic-warehouse", "basic-warehouse-create", "新增", "button", "", "", "basic:warehouse:create", "", 1),
    ("basic-warehouse", "basic-warehouse-update", "编辑", "button", "", "", "basic:warehouse:update", "", 2),
    ("basic-warehouse", "basic-warehouse-delete", "删除", "button", "", "", "basic:warehouse:delete", "", 3),
    ("basic-location", "basic-location-create", "新增", "button", "", "", "basic:location:create", "", 1),
    ("basic-location", "basic-location-update", "编辑", "button", "", "", "basic:location:update", "", 2),
    ("basic-location", "basic-location-delete", "删除", "button", "", "", "basic:location:delete", "", 3),
    ("basic-goods", "basic-goods-create", "新增", "button", "", "", "basic:goods:create", "", 1),
    ("basic-goods", "basic-goods-update", "编辑", "button", "", "", "basic:goods:update", "", 2),
    ("basic-goods", "basic-goods-delete", "删除", "button", "", "", "basic:goods:delete", "", 3),
    ("basic-partner", "basic-partner-create", "新增", "button", "", "", "basic:supplier:create", "", 1),
    ("basic-partner", "basic-partner-update", "编辑", "button", "", "", "basic:supplier:update", "", 2),
    ("basic-partner", "basic-partner-delete", "删除", "button", "", "", "basic:supplier:delete", "", 3),
    ("inbound-order", "inbound-create", "创建", "button", "", "", "inbound:order:create", "", 1),
    ("inbound-order", "inbound-execute", "执行", "button", "", "", "inbound:order:execute", "", 2),
    ("inbound-order", "inbound-cancel", "作废", "button", "", "", "inbound:order:cancel", "", 3),
    ("outbound-order", "outbound-create", "创建", "button", "", "", "outbound:order:create", "", 1),
    ("outbound-order", "outbound-execute", "执行", "button", "", "", "outbound:order:execute", "", 2),
    ("outbound-order", "outbound-cancel", "作废", "button", "", "", "outbound:order:cancel", "", 3),
    ("inv-move", "inventory-move", "执行移库", "button", "", "", "inventory:move", "", 1),
    ("inv-transfer", "inv-transfer-create", "创建调拨", "button", "", "", "inventory:transfer:create", "", 1),
    ("inv-transfer", "inv-transfer-execute", "执行调拨", "button", "", "", "inventory:transfer:execute", "", 2),
    ("stocktake-order", "stocktake-create", "创建盘点", "button", "", "", "stocktake:order:create", "", 1),
    ("stocktake-order", "stocktake-record", "录入实盘", "button", "", "", "stocktake:order:update", "", 2),
    ("stocktake-order", "stocktake-finish", "完成盘点", "button", "", "", "stocktake:order:finish", "", 3),
    ("sys-user", "sys-user-create", "新增", "button", "", "", "system:user:create", "", 1),
    ("sys-user", "sys-user-update", "编辑", "button", "", "", "system:user:update", "", 2),
    ("sys-user", "sys-user-delete", "删除", "button", "", "", "system:user:delete", "", 3),
    ("sys-role", "sys-role-create", "新增", "button", "", "", "system:role:create", "", 1),
    ("sys-role", "sys-role-update", "编辑", "button", "", "", "system:role:update", "", 2),
    ("sys-role", "sys-role-delete", "删除", "button", "", "", "system:role:delete", "", 3),
    ("sys-menu", "sys-menu-create", "新增", "button", "", "", "system:menu:create", "", 1),
    ("sys-menu", "sys-menu-update", "编辑", "button", "", "", "system:menu:update", "", 2),
    ("sys-menu", "sys-menu-delete", "删除", "button", "", "", "system:menu:delete", "", 3),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # admin 用户
        user = (await db.execute(select(SysUser).where(SysUser.username == "admin"))).scalar_one_or_none()
        if user is None:
            user = SysUser(
                username="admin",
                password_hash=hash_password("admin123"),
                nickname="系统管理员",
                is_super=True,
            )
            db.add(user)
            print("已创建 admin 用户（密码 admin123）")

        # 菜单
        existing = (await db.execute(select(SysMenu))).scalars().all()
        if not existing:
            key_to_id: dict[str, int] = {}
            for parent_key, key, name, mtype, path, component, perm, icon, sort in MENUS:
                menu = SysMenu(
                    parent_id=key_to_id.get(parent_key or "", 0),
                    name=name, type=mtype, path=path, component=component,
                    perm_code=perm, icon=icon, sort=sort,
                )
                db.add(menu)
                await db.flush()
                key_to_id[key] = menu.id
            print(f"已创建 {len(MENUS)} 条菜单")

        # 示例仓库
        wh = (await db.execute(select(Warehouse).where(Warehouse.code == "WH01"))).scalar_one_or_none()
        if wh is None:
            wh = Warehouse(code="WH01", name="主仓库", address="默认示例仓库", contact="", phone="")
            db.add(wh)
            await db.flush()
            zones = [
                Zone(warehouse_id=wh.id, code="RECV", name="收货区", type="receiving"),
                Zone(warehouse_id=wh.id, code="STORE", name="存储区", type="storage"),
                Zone(warehouse_id=wh.id, code="PICK", name="拣货区", type="picking"),
            ]
            db.add_all(zones)
            await db.flush()
            locs = []
            for zi, (zone, rows, cols) in enumerate(zip(zones, [2, 4, 2], [4, 6, 4])):
                for r in range(1, rows + 1):
                    for c in range(1, cols + 1):
                        locs.append(Location(warehouse_id=wh.id, zone_id=zone.id, code=f"{zone.code}-{r:02d}-{c:02d}"))
            db.add_all(locs)
            print(f"已创建示例仓库 WH01（{len(zones)} 个库区 {len(locs)} 个库位）")

        # 商品分类示例
        cat = (await db.execute(select(GoodsCategory).where(GoodsCategory.name == "通用分类"))).scalar_one_or_none()
        if cat is None:
            db.add(GoodsCategory(name="通用分类", sort=0))
            print("已创建示例商品分类")

        # admin 关联仓库
        existing_link = await db.execute(
            select(SysUserWarehouse).where(SysUserWarehouse.user_id == user.id)
        )
        if existing_link.first() is None:
            db.add(SysUserWarehouse(user_id=user.id, warehouse_id=wh.id))

        await db.commit()
        print("种子数据初始化完成")


if __name__ == "__main__":
    asyncio.run(seed())
