import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.service import router as ai_router
from app.api.v1 import auth, basic, dashboard, export, inventory, order, stocktake, system, transfer
from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.database import engine
from app.models import Base

logger = logging.getLogger("wms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    # 开发环境直接建表；生产环境后续切换 Alembic 迁移
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表结构已就绪")
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "PUT", "DELETE") and request.url.path.startswith("/api/"):
        logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


for r in (
    auth.router, system.router, basic.router, order.router, inventory.router,
    transfer.router, stocktake.router, dashboard.router, export.router, ai_router,
):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
