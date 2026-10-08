from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PkMixin, SoftDeleteMixin, TimestampMixin


class Warehouse(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "warehouse"

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200), default="")
    contact: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(String(200), default="")


class Zone(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "zone"

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    # receiving=收货区 storage=存储区 picking=拣货区 returns=退货区 other=其他
    type: Mapped[str] = mapped_column(String(20), default="storage")
    remark: Mapped[str] = mapped_column(String(200), default="")


class Location(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "location"
    __table_args__ = (UniqueConstraint("code", "is_deleted", name="uq_location_code"),)

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zone.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(String(200), default="")


class GoodsCategory(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "goods_category"

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    name: Mapped[str] = mapped_column(String(50))
    sort: Mapped[int] = mapped_column(default=0)


class Goods(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "goods"

    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)  # SKU0001
    name: Mapped[str] = mapped_column(String(100), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("goods_category.id"))
    unit: Mapped[str] = mapped_column(String(20), default="个")
    spec: Mapped[str] = mapped_column(String(100), default="")
    barcode: Mapped[str] = mapped_column(String(50), default="", index=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 参考单价
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"))
    min_stock: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 下限预警
    max_stock: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 上限预警
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(String(200), default="")


class Supplier(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "supplier"

    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)  # SUP0001
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    remark: Mapped[str] = mapped_column(String(200), default="")


class Customer(Base, PkMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customer"

    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)  # CUS0001
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    remark: Mapped[str] = mapped_column(String(200), default="")


class Inventory(Base, PkMixin, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("goods_id", "warehouse_id", "location_id", name="uq_inventory_key"),)

    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), index=True)
    qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class InventoryTransaction(Base, PkMixin):
    __tablename__ = "inventory_transaction"

    order_no: Mapped[str] = mapped_column(String(40), index=True)
    # purchase_in/return_in/other_in/sale_out/use_out/other_out/move/transfer_in/transfer_out/stocktake
    biz_type: Mapped[str] = mapped_column(String(20), index=True)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouse.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), index=True)
    qty: Mapped[float] = mapped_column(Numeric(12, 2))  # 正=入库 负=出库
    before_qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    after_qty: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    operator_name: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
