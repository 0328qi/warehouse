from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PkMixin, TimestampMixin

# 单据状态
STATUS_DRAFT = "draft"  # 草稿，可编辑
STATUS_EXECUTED = "executed"  # 已执行，库存已变动
STATUS_CANCELLED = "cancelled"  # 已作废


class InboundOrder(Base, PkMixin, TimestampMixin):
    __tablename__ = "inbound_order"

    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    # purchase=采购入库 return=退货入库 other=其他入库
    type: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"))
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, index=True)
    total_qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remark: Mapped[str] = mapped_column(String(200), default="")
    creator_id: Mapped[int | None]
    creator_name: Mapped[str] = mapped_column(String(50), default="")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)


class InboundItem(Base, PkMixin):
    __tablename__ = "inbound_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("inbound_order.id"), index=True)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"))
    qty: Mapped[float] = mapped_column(Numeric(12, 2))
    remark: Mapped[str] = mapped_column(String(200), default="")


class OutboundOrder(Base, PkMixin, TimestampMixin):
    __tablename__ = "outbound_order"

    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    # sale=销售出库 use=领用出库 other=其他出库
    type: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.id"))
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, index=True)
    total_qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remark: Mapped[str] = mapped_column(String(200), default="")
    creator_id: Mapped[int | None]
    creator_name: Mapped[str] = mapped_column(String(50), default="")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)


class OutboundItem(Base, PkMixin):
    __tablename__ = "outbound_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("outbound_order.id"), index=True)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"))
    qty: Mapped[float] = mapped_column(Numeric(12, 2))
    remark: Mapped[str] = mapped_column(String(200), default="")


class TransferOrder(Base, PkMixin, TimestampMixin):
    __tablename__ = "transfer_order"

    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, index=True)
    remark: Mapped[str] = mapped_column(String(200), default="")
    creator_id: Mapped[int | None]
    creator_name: Mapped[str] = mapped_column(String(50), default="")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)


class TransferItem(Base, PkMixin):
    __tablename__ = "transfer_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("transfer_order.id"), index=True)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"))
    from_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"))
    to_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"))
    qty: Mapped[float] = mapped_column(Numeric(12, 2))


class StocktakeOrder(Base, PkMixin, TimestampMixin):
    __tablename__ = "stocktake_order"

    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zone.id"))  # 不选=全仓
    # processing=进行中 finished=已完成 cancelled=已作废
    status: Mapped[str] = mapped_column(String(20), default="processing", index=True)
    remark: Mapped[str] = mapped_column(String(200), default="")
    creator_id: Mapped[int | None]
    creator_name: Mapped[str] = mapped_column(String(50), default="")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class StocktakeItem(Base, PkMixin):
    __tablename__ = "stocktake_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("stocktake_order.id"), index=True)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"))
    book_qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 账面数量
    actual_qty: Mapped[float | None] = mapped_column(Numeric(12, 2))  # 实盘数量，None=未盘
