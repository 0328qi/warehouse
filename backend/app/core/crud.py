from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class PageResult(BaseModel):
    total: int
    items: list[Any]


async def paginate(db: AsyncSession, stmt: Select, page: int, page_size: int) -> tuple[int, list]:
    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
    return total, result.scalars().all()


def apply_soft_delete_filters(stmt: Select, model: type[Base]) -> Select:
    if hasattr(model, "is_deleted"):
        stmt = stmt.where(model.is_deleted.is_(False))
    return stmt


async def soft_delete(db: AsyncSession, obj: Base) -> None:
    obj.is_deleted = True  # type: ignore[attr-defined]
    await db.commit()


async def hard_delete(db: AsyncSession, model: type[Base], obj_id: int) -> None:
    await db.execute(delete(model).where(model.id == obj_id))
    await db.commit()


def not_found(detail: str = "数据不存在") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
