from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.constants import Role
from app.models import User
from app.utils.filtering import text_search


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def list_stmt(role: Role | None = None, is_active: bool | None = None, q: str | None = None) -> Select:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    cond = text_search([User.email, User.full_name], q)
    if cond is not None:
        stmt = stmt.where(cond)
    return stmt


def active_user_ids_by_roles(db: Session, roles: tuple[Role, ...]) -> list[int]:
    return list(db.scalars(select(User.id).where(User.role.in_(roles), User.is_active.is_(True))).all())
