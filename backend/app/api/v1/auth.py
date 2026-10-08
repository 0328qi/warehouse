from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, oauth2_scheme
from app.core.security import create_token, decode_token, verify_password
from app.models import SysMenu, SysUser
from app.schemas.system import LoginRequest, TokenOut, UserInfoOut

router = APIRouter(prefix="/auth", tags=["认证"])

ACCESS_EXPIRE = 720
REFRESH_EXPIRE = 7 * 24 * 60


def build_user_info(user: SysUser, all_menus: list = None) -> dict:
    if user.is_super:
        menus = all_menus or []
    else:
        menus = [m for role in user.roles for m in role.menus]
    perm_codes = sorted({m.perm_code for m in menus if m.perm_code})
    if user.is_super:
        perm_codes = ["*"]
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "is_super": user.is_super,
        "roles": [r.code for r in user.roles],
        "perm_codes": perm_codes,
        "warehouse_ids": [w.id for w in user.warehouses],
        "menus": [
            {
                "id": m.id, "parent_id": m.parent_id, "name": m.name, "type": m.type,
                "path": m.path, "component": m.component, "perm_code": m.perm_code,
                "icon": m.icon, "sort": m.sort, "visible": m.visible,
            }
            for m in menus
        ],
    }


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SysUser).where(SysUser.username == body.username, SysUser.is_deleted.is_(False)))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return TokenOut(
        access_token=create_token(user.id, ACCESS_EXPIRE, "access"),
        refresh_token=create_token(user.id, REFRESH_EXPIRE, "refresh"),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="refresh token 无效") from None
    result = await db.execute(select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted.is_(False)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="refresh token 无效")
    return TokenOut(
        access_token=create_token(user.id, ACCESS_EXPIRE, "access"),
        refresh_token=create_token(user.id, REFRESH_EXPIRE, "refresh"),
    )


@router.get("/me", response_model=UserInfoOut)
async def me(current: SysUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    all_menus = list((await db.execute(select(SysMenu).order_by(SysMenu.sort, SysMenu.id))).scalars().all())
    return UserInfoOut(**build_user_info(current, all_menus))
