from datetime import datetime

from pydantic import BaseModel

from app.schemas.system import ORMModel


class OrderItemIn(BaseModel):
    goods_id: int
    location_id: int
    qty: float
    remark: str = ""


class InboundCreate(BaseModel):
    type: str  # purchase/return/other
    warehouse_id: int
    supplier_id: int | None = None
    remark: str = ""
    items: list[OrderItemIn]


class InboundUpdate(BaseModel):
    type: str | None = None
    supplier_id: int | None = None
    remark: str = ""
    items: list[OrderItemIn]


class InboundItemOut(ORMModel):
    id: int
    goods_id: int
    location_id: int
    qty: float
    remark: str
    goods_name: str = ""
    goods_code: str = ""
    location_code: str = ""


class OrderOut(ORMModel):
    id: int
    order_no: str
    type: str
    warehouse_id: int
    supplier_id: int | None = None
    customer_id: int | None = None
    status: str
    total_qty: float
    remark: str
    creator_name: str
    executed_at: datetime | None
    created_at: datetime
    warehouse_name: str = ""
    supplier_name: str = ""
    customer_name: str = ""
    items: list[InboundItemOut] = []


class OutboundCreate(BaseModel):
    type: str  # sale/use/other
    warehouse_id: int
    customer_id: int | None = None
    remark: str = ""
    items: list[OrderItemIn]


class OutboundUpdate(BaseModel):
    type: str | None = None
    customer_id: int | None = None
    remark: str = ""
    items: list[OrderItemIn]


class TransferItemIn(BaseModel):
    goods_id: int
    from_location_id: int
    to_location_id: int
    qty: float


class TransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    remark: str = ""
    items: list[TransferItemIn]


class TransferItemOut(ORMModel):
    id: int
    goods_id: int
    from_location_id: int
    to_location_id: int
    qty: float
    goods_name: str = ""
    goods_code: str = ""
    from_location_code: str = ""
    to_location_code: str = ""


class TransferOut(ORMModel):
    id: int
    order_no: str
    from_warehouse_id: int
    to_warehouse_id: int
    status: str
    remark: str
    creator_name: str
    executed_at: datetime | None
    created_at: datetime
    from_warehouse_name: str = ""
    to_warehouse_name: str = ""
    items: list[TransferItemOut] = []


# ---- Stocktake ----
class StocktakeCreate(BaseModel):
    warehouse_id: int
    zone_id: int | None = None  # 不选=全仓
    remark: str = ""


class StocktakeRecordIn(BaseModel):
    item_id: int
    actual_qty: float


class StocktakeItemOut(ORMModel):
    id: int
    goods_id: int
    location_id: int
    book_qty: float
    actual_qty: float | None
    goods_name: str = ""
    goods_code: str = ""
    location_code: str = ""


class StocktakeOut(ORMModel):
    id: int
    order_no: str
    warehouse_id: int
    zone_id: int | None
    status: str
    remark: str
    creator_name: str
    finished_at: datetime | None
    created_at: datetime
    warehouse_name: str = ""
    zone_name: str = ""
    item_count: int = 0
    diff_count: int = 0
