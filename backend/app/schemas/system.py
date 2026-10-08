from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfoOut(ORMModel):
    id: int
    username: str
    nickname: str
    is_super: bool
    roles: list[str] = []
    perm_codes: list[str] = []
    warehouse_ids: list[int] = []
    menus: list[dict] = []


# ---- 通用 ----
class PageQuery(BaseModel):
    page: int = 1
    page_size: int = 20


class IdIn(BaseModel):
    ids: list[int]


class MsgOut(BaseModel):
    message: str = "ok"


class RoleBriefOut(ORMModel):
    id: int
    name: str
    code: str


# ---- System: User ----
class UserCreate(BaseModel):
    username: str
    password: str
    nickname: str = ""
    phone: str = ""
    email: str = ""
    is_active: bool = True
    role_ids: list[int] = []
    warehouse_ids: list[int] = []


class UserUpdate(BaseModel):
    nickname: str = ""
    phone: str = ""
    email: str = ""
    is_active: bool = True
    password: str | None = None  # 传了则重置
    role_ids: list[int] | None = None
    warehouse_ids: list[int] | None = None


class UserOut(ORMModel):
    id: int
    username: str
    nickname: str
    phone: str
    email: str
    is_active: bool
    is_super: bool
    created_at: datetime
    roles: list[RoleBriefOut] = []
    warehouse_ids: list[int] = []


# ---- System: Role ----
class RoleCreate(BaseModel):
    name: str
    code: str
    remark: str = ""
    menu_ids: list[int] = []


class RoleUpdate(BaseModel):
    name: str = ""
    remark: str = ""
    menu_ids: list[int] | None = None


class RoleOut(ORMModel):
    id: int
    name: str
    code: str
    remark: str
    created_at: datetime
    menu_ids: list[int] = []


# ---- System: Menu ----
class MenuCreate(BaseModel):
    parent_id: int = 0
    name: str
    type: str = "menu"  # dir/menu/button
    path: str = ""
    component: str = ""
    perm_code: str = ""
    icon: str = ""
    sort: int = 0
    visible: bool = True


class MenuUpdate(MenuCreate):
    pass


class MenuOut(ORMModel):
    id: int
    parent_id: int
    name: str
    type: str
    path: str
    component: str
    perm_code: str
    icon: str
    sort: int
    visible: bool


class MenuTreeNode(MenuOut):
    children: list["MenuTreeNode"] = []


MenuTreeNode.model_rebuild()
