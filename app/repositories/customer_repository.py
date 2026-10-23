from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Customer
from app.utils.filtering import text_search


def get(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def get_by_user_id(db: Session, user_id: int) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.user_id == user_id))


def get_by_email(db: Session, email: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.email == email.lower()))


def search_stmt(q: str | None = None, is_active: bool | None = None, company: str | None = None) -> Select:
    stmt = select(Customer)
    cond = text_search([Customer.name, Customer.email, Customer.phone, Customer.company], q)
    if cond is not None:
        stmt = stmt.where(cond)
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)
    if company:
        stmt = stmt.where(Customer.company.ilike(company))
    return stmt
