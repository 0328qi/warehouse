from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import bad_request, not_found, paginate, soft_delete
from app.core.database import get_db
from app.core.deps import get_current_user, require_perm
from app.core.security import hash_password
from app.models import SysMenu, SysRole, SysUser, SysUserWarehouse, SysUserRole
from app.schemas.system import (
    MenuCreate,
    MenuOut,
    MenuTreeNode,
    MsgOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/system", tags=["系统管理"])


def _user_to_out(user: SysUser) -> dict:
    data = UserOut.model_validate(user).model_dump()
    data["warehouse_ids"] = [w.id for w in user.warehouses]
    return data


# ============ 用户 ============
@router.get("/users", dependencies=[Depends(require_perm("system:user:list"))])
async def list_users(
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    stmt = select(SysUser).where(SysUser.is_deleted.is_(False)).order_by(SysUser.id.desc())
    if keyword:
        stmt = stmt.where(SysUser.username.contains(keyword) | SysUser.nickname.contains(keyword))
    total, users = await paginate(db, stmt, page, page_size)
    return {"total": total, "items": [_user_to_out(u) for u in users]}


@router.post("/users", dependencies=[Depends(require_perm("system:user:create"))])
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(SysUser).where(SysUser.username == body.username))
    if exists.scalar_one_or_none():
        raise bad_request("用户名已存在")
    user = SysUser(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        phone=body.phone,
        email=body.email,
        is_active=body.is_active,
    )
    if body.role_ids:
        roles = (await db.execute(select(SysRole).where(SysRole.id.in_(body.role_ids)))).scalars().all()
        user.roles = list(roles)
    if body.warehouse_ids:
        from app.models import Warehouse

        warehouses = (await db.execute(select(Warehouse).where(Warehouse.id.in_(body.warehouse_ids)))).scalars().all()
        user.warehouses = list(warehouses)
    db.add(user)
    await db.commit()
    return _user_to_out(user)


@router.put("/users/{user_id}", dependencies=[Depends(require_perm("system:user:update"))])
async def update_user(user_id: int, body: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted.is_(False)))
    ).scalar_one_or_none()
    if not user:
        raise not_found("用户不存在")
    user.nickname = body.nickname or user.nickname
    user.phone = body.phone
    user.email = body.email
    user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)
    if body.role_ids is not None:
        roles = (await db.execute(select(SysRole).where(SysRole.id.in_(body.role_ids)))).scalars().all()
        user.roles = list(roles)
    if body.warehouse_ids is not None:
        from app.models import Warehouse

        warehouses = (await db.execute(select(Warehouse).where(Warehouse.id.in_(body.warehouse_ids)))).scalars().all()
        user.warehouses = list(warehouses)
    await db.commit()
    return _user_to_out(user)


@router.delete("/users/{user_id}", dependencies=[Depends(require_perm("system:user:delete"))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current: SysUser = Depends(get_current_user)):
    if user_id == current.id:
        raise bad_request("不能删除自己")
    user = await db.get(SysUser, user_id)
    if not user:
        raise not_found()
    await soft_delete(db, user)
    return MsgOut()


# ============ 角色 ============
@router.get("/roles", dependencies=[Depends(require_perm("system:role:list"))])
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SysRole).where(SysRole.is_deleted.is_(False)).order_by(SysRole.id)
    total, roles = await paginate(db, stmt, page, page_size)
    items = [{**RoleOut.model_validate(r).model_dump(), "menu_ids": [m.id for m in r.menus]} for r in roles]
    return {"total": total, "items": items}


@router.get("/roles/all", dependencies=[Depends(get_current_user)])
async def all_roles(db: AsyncSession = Depends(get_db)):
    roles = (await db.execute(select(SysRole).where(SysRole.is_deleted.is_(False)).order_by(SysRole.id))).scalars().all()
    return [{"id": r.id, "name": r.name, "code": r.code} for r in roles]


@router.post("/roles", dependencies=[Depends(require_perm("system:role:create"))])
async def create_role(body: RoleCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(SysRole).where(SysRole.code == body.code, SysRole.is_deleted.is_(False)))
    if exists.scalar_one_or_none():
        raise bad_request("角色编码已存在")
    role = SysRole(name=body.name, code=body.code, remark=body.remark)
    if body.menu_ids:
        menus = (await db.execute(select(SysMenu).where(SysMenu.id.in_(body.menu_ids)))).scalars().all()
        role.menus = list(menus)
    db.add(role)
    await db.commit()
    return RoleOut.model_validate(role)


@router.put("/roles/{role_id}", dependencies=[Depends(require_perm("system:role:update"))])
async def update_role(role_id: int, body: RoleUpdate, db: AsyncSession = Depends(get_db)):
    role = await db.get(SysRole, role_id)
    if not role or role.is_deleted:
        raise not_found("角色不存在")
    if body.name:
        role.name = body.name
    role.remark = body.remark
    if body.menu_ids is not None:
        menus = (await db.execute(select(SysMenu).where(SysMenu.id.in_(body.menu_ids)))).scalars().all()
        role.menus = list(menus)
    await db.commit()
    return MsgOut()


@router.delete("/roles/{role_id}", dependencies=[Depends(require_perm("system:role:delete"))])
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)):
    role = await db.get(SysRole, role_id)
    if not role:
        raise not_found()
    await soft_delete(db, role)
    return MsgOut()


# ============ 菜单 ============
def _build_menu_tree(menus: list[SysMenu], parent_id: int = 0) -> list[dict]:
    nodes = []
    for m in sorted([m for m in menus if m.parent_id == parent_id], key=lambda x: (x.sort, x.id)):
        node = MenuOut.model_validate(m).model_dump()
        node["children"] = _build_menu_tree(menus, m.id)
        nodes.append(node)
    return nodes


@router.get("/menus/tree", dependencies=[Depends(get_current_user)])
async def menu_tree(db: AsyncSession = Depends(get_db)):
    menus = (await db.execute(select(SysMenu).order_by(SysMenu.sort, SysMenu.id))).scalars().all()
    return _build_menu_tree(list(menus))


@router.post("/menus", dependencies=[Depends(require_perm("system:menu:create"))])
async def create_menu(body: MenuCreate, db: AsyncSession = Depends(get_db)):
    menu = SysMenu(**body.model_dump())
    db.add(menu)
    await db.commit()
    return MenuOut.model_validate(menu)


@router.put("/menus/{menu_id}", dependencies=[Depends(require_perm("system:menu:update"))])
async def update_menu(menu_id: int, body: MenuCreate, db: AsyncSession = Depends(get_db)):
    menu = await db.get(SysMenu, menu_id)
    if not menu:
        raise not_found()
    for k, v in body.model_dump().items():
        setattr(menu, k, v)
    await db.commit()
    return MenuOut.model_validate(menu)


@router.delete("/menus/{menu_id}", dependencies=[Depends(require_perm("system:menu:delete"))])
async def delete_menu(menu_id: int, db: AsyncSession = Depends(get_db)):
    children = await db.execute(select(SysMenu).where(SysMenu.parent_id == menu_id))
    if children.scalar_one_or_none():
        raise bad_request("存在子菜单，不能删除")
    menu = await db.get(SysMenu, menu_id)
    if not menu:
        raise not_found()
    await db.delete(menu)
    await db.commit()
    return MsgOut()
