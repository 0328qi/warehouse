from datetime import datetime

from pydantic import BaseModel

from app.schemas.system import ORMModel


# ---- Warehouse ----
class WarehouseCreate(BaseModel):
    code: str
    name: str
    address: str = ""
    contact: str = ""
    phone: str = ""
    status: bool = True
    remark: str = ""


class WarehouseUpdate(BaseModel):
    name: str = ""
    address: str = ""
    contact: str = ""
    phone: str = ""
    status: bool = True
    remark: str = ""


class WarehouseOut(ORMModel):
    id: int
    code: str
    name: str
    address: str
    contact: str
    phone: str
    status: bool
    remark: str
    created_at: datetime


# ---- Zone ----
class ZoneCreate(BaseModel):
    warehouse_id: int
    code: str
    name: str
    type: str = "storage"
    remark: str = ""


class ZoneUpdate(BaseModel):
    name: str = ""
    type: str = "storage"
    remark: str = ""


class ZoneOut(ORMModel):
    id: int
    warehouse_id: int
    code: str
    name: str
    type: str
    remark: str
    created_at: datetime


# ---- Location ----
class LocationCreate(BaseModel):
    warehouse_id: int
    zone_id: int
    code: str
    status: bool = True
    remark: str = ""


class LocationBatchCreate(BaseModel):
    """按前缀批量生成库位：如 zone 内 rows=3 cols=4 → A-01-01 ~ A-03-04"""

    warehouse_id: int
    zone_id: int
    prefix: str
    rows: int
    cols: int


class LocationUpdate(BaseModel):
    status: bool = True
    remark: str = ""


class LocationOut(ORMModel):
    id: int
    warehouse_id: int
    zone_id: int
    code: str
    status: bool
    remark: str
    created_at: datetime


# ---- Goods Category ----
class CategoryCreate(BaseModel):
    parent_id: int = 0
    name: str
    sort: int = 0


class CategoryUpdate(BaseModel):
    name: str = ""
    sort: int = 0


class CategoryOut(ORMModel):
    id: int
    parent_id: int
    name: str
    sort: int


class CategoryTreeNode(CategoryOut):
    children: list["CategoryTreeNode"] = []


CategoryTreeNode.model_rebuild()


# ---- Goods ----
class GoodsCreate(BaseModel):
    name: str
    category_id: int | None = None
    unit: str = "个"
    spec: str = ""
    barcode: str = ""
    price: float = 0
    supplier_id: int | None = None
    min_stock: float = 0
    max_stock: float = 0
    status: bool = True
    remark: str = ""


class GoodsUpdate(BaseModel):
    name: str = ""
    category_id: int | None = None
    unit: str = "个"
    spec: str = ""
    barcode: str = ""
    price: float = 0
    supplier_id: int | None = None
    min_stock: float = 0
    max_stock: float = 0
    status: bool = True
    remark: str = ""


class GoodsOut(ORMModel):
    id: int
    code: str
    name: str
    category_id: int | None
    unit: str
    spec: str
    barcode: str
    price: float
    supplier_id: int | None
    min_stock: float
    max_stock: float
    status: bool
    remark: str
    created_at: datetime


# ---- Supplier / Customer ----
class PartnerCreate(BaseModel):
    name: str
    contact: str = ""
    phone: str = ""
    address: str = ""
    remark: str = ""


class PartnerUpdate(BaseModel):
    name: str = ""
    contact: str = ""
    phone: str = ""
    address: str = ""
    remark: str = ""


class PartnerOut(ORMModel):
    id: int
    code: str
    name: str
    contact: str
    phone: str
    address: str
    remark: str
    created_at: datetime


# ---- Inventory ----
class InventoryBalanceOut(ORMModel):
    id: int
    goods_id: int
    warehouse_id: int
    location_id: int
    qty: float
    goods_name: str = ""
    goods_code: str = ""
    unit: str = ""
    warehouse_name: str = ""
    location_code: str = ""


class InventoryTransactionOut(ORMModel):
    id: int
    order_no: str
    biz_type: str
    goods_id: int
    warehouse_id: int
    location_id: int
    qty: float
    before_qty: float
    after_qty: float
    operator_name: str
    created_at: datetime
    goods_name: str = ""
    warehouse_name: str = ""
    location_code: str = ""


class MoveIn(BaseModel):
    """库位间移库"""

    goods_id: int
    from_location_id: int
    to_location_id: int
    qty: float


class OrderNoOut(BaseModel):
    order_no: str
