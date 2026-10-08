import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.crud import bad_request
from app.models import Inventory, InventoryTransaction


async def generate_order_no(db: AsyncSession, prefix: str) -> str:
    """单号规则：{前缀}{日期}-{当日序号}，如 IN20261004-0001。
    Redis 可用时 INCR 保证唯一；不可用时降级为 时间戳+随机后缀。"""
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        from app.core.cache import redis_available

        if redis_available:
            redis = get_redis()
            key = f"seq:{prefix}:{date_str}"
            seq = await redis.incr(key)
            if seq == 1:
                await redis.expire(key, 172800)  # 2 天过期
            return f"{prefix}{date_str}-{seq:04d}"
    except Exception:
        pass
    # 降级：同秒并发由后 4 位随机数兜底，冲突概率可忽略
    suffix = datetime.now().strftime("%H%M%S") + f"{random.randint(0, 9999):04d}"
    return f"{prefix}{date_str}-{suffix}"


async def get_or_create_inventory(
    db: AsyncSession, goods_id: int, warehouse_id: int, location_id: int, for_update: bool = False
) -> Inventory:
    stmt = select(Inventory).where(
        Inventory.goods_id == goods_id,
        Inventory.warehouse_id == warehouse_id,
        Inventory.location_id == location_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if inv is None:
        inv = Inventory(goods_id=goods_id, warehouse_id=warehouse_id, location_id=location_id, qty=0)
        db.add(inv)
        await db.flush()
    return inv


async def apply_stock_change(
    db: AsyncSession,
    *,
    goods_id: int,
    warehouse_id: int,
    location_id: int,
    qty_change: float,
    biz_type: str,
    order_no: str,
    operator_id: int | None,
    operator_name: str,
) -> Inventory:
    """库存变动唯一入口：行锁防并发超扣，写入不可变流水。qty_change 正=入 负=出。"""
    inv = await get_or_create_inventory(db, goods_id, warehouse_id, location_id, for_update=True)
    before = float(inv.qty)
    after = before + qty_change
    if after < 0:
        await db.rollback()
        raise bad_request(f"库存不足：当前 {before}，需要扣减 {-qty_change}")

    inv.qty = after
    db.add(
        InventoryTransaction(
            order_no=order_no,
            biz_type=biz_type,
            goods_id=goods_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            qty=qty_change,
            before_qty=before,
            after_qty=after,
            operator_id=operator_id,
            operator_name=operator_name,
        )
    )
    await db.flush()
    return inv


async def warehouse_total_qty(db: AsyncSession, warehouse_id: int) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(Inventory.qty), 0)).where(Inventory.warehouse_id == warehouse_id)
    )
    return float(result.scalar_one())
