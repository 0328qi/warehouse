from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import SysUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> SysUser:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id = int(payload["sub"])
    except Exception:
        raise credentials_exc from None

    result = await db.execute(select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted.is_(False)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_perm(perm_code: str):
    """接口级权限校验：超级管理员放行，否则校验角色关联的菜单按钮权限。"""

    async def checker(user: SysUser = Depends(get_current_user)) -> SysUser:
        if user.is_super:
            return user
        perm_codes = {m.perm_code for role in user.roles for m in role.menus if m.perm_code}
        if perm_code not in perm_codes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无操作权限：{perm_code}")
        return user

    return checker


def get_warehouse_scope(user: SysUser) -> list[int] | None:
    """数据权限：返回用户可见仓库 id 列表；超级管理员返回 None 表示不限制。"""
    if user.is_super:
        return None
    return [w.id for w in user.warehouses]
