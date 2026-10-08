from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PkMixin, SoftDeleteMixin, TimestampMixin


class SysUser(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    nickname: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_super: Mapped[bool] = mapped_column(Boolean, default=False)

    roles = relationship("SysRole", secondary="sys_user_role", lazy="selectin")
    warehouses = relationship("Warehouse", secondary="sys_user_warehouse", lazy="selectin")


class SysRole(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_role"

    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    remark: Mapped[str] = mapped_column(String(200), default="")

    menus = relationship("SysMenu", secondary="sys_role_menu", lazy="selectin")


class SysMenu(Base, PkMixin, TimestampMixin):
    __tablename__ = "sys_menu"

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    name: Mapped[str] = mapped_column(String(50))
    # dir=目录 menu=页面 button=按钮
    type: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(200), default="")
    component: Mapped[str] = mapped_column(String(200), default="")
    perm_code: Mapped[str] = mapped_column(String(100), default="", index=True)
    icon: Mapped[str] = mapped_column(String(50), default="")
    sort: Mapped[int] = mapped_column(default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id"), primary_key=True)


class SysRoleMenu(Base):
    __tablename__ = "sys_role_menu"
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id"), primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("sys_menu.id"), primary_key=True)


class SysUserWarehouse(Base):
    __tablename__ = "sys_user_warehouse"
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), primary_key=True)


class SysOperationLog(Base, PkMixin):
    __tablename__ = "sys_operation_log"

    user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(String(50), default="")
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
