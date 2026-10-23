import math
from typing import Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class PageParams:
    """Shared pagination + sorting query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        sort_by: str | None = Query(None, description="Field to sort by (see endpoint docs)"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    ):
        self.page = page
        self.size = size
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def paginate(db: Session, stmt: Select, params: PageParams, *, scalars: bool = True) -> tuple[list[Any], int]:
    """Run COUNT + LIMIT/OFFSET so only one page of rows is ever loaded."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    result = db.execute(stmt.limit(params.size).offset(params.offset))
    items = list(result.scalars().all()) if scalars else list(result.all())
    return items, total


def make_page(items: list[Any], total: int, params: PageParams) -> dict:
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": math.ceil(total / params.size) if total else 0,
    }
