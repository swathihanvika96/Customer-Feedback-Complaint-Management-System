from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Category
from app.utils.filtering import text_search


def get(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(func.lower(Category.name) == name.strip().lower()))


def search_stmt(q: str | None = None, is_active: bool | None = None) -> Select:
    stmt = select(Category)
    if is_active is not None:
        stmt = stmt.where(Category.is_active == is_active)
    cond = text_search([Category.name, Category.description], q)
    if cond is not None:
        stmt = stmt.where(cond)
    return stmt
