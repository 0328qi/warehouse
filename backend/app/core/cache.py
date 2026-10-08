import json
import logging
import time

from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("wms.cache")

redis_client: aioredis.Redis | None = None
redis_available: bool = False


async def init_redis() -> None:
    global redis_client, redis_available
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        redis_available = True
        logger.info("Redis 已连接")
    except Exception as exc:  # 开发环境允许无 Redis 降级运行
        redis_client = None
        redis_available = False
        logger.warning("Redis 不可用，已降级运行（%s）", exc)


async def close_redis() -> None:
    global redis_client, redis_available
    if redis_client:
        await redis_client.aclose()
        redis_client = None
    redis_available = False


def get_redis() -> aioredis.Redis:
    if not redis_available or redis_client is None:
        raise RuntimeError("Redis 未连接")
    return redis_client


class DistributedLock:
    """基于 Redis SET NX 的分布式锁，用于跨仓调拨等需要原子性的操作。
    Redis 不可用时降级为空锁：单实例部署下数据库事务仍保证一致性。"""

    def __init__(self, key: str, timeout: int = 10):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.token = str(time.time_ns())

    async def __aenter__(self) -> "DistributedLock":
        if redis_available:
            client = get_redis()
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                if await client.set(self.key, self.token, nx=True, ex=self.timeout):
                    return self
                await client.sleep(0.05)
            raise RuntimeError("获取锁超时，请稍后重试")
        return self

    async def __aexit__(self, *args) -> None:
        if redis_available:
            get_redis().delete(self.key)


def cache_json(key: str, value: dict, ttl: int = 60) -> None:
    if redis_available:
        get_redis().set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
