"""Seed data: SLA rules, default categories and (optionally) the first admin.

Run manually after migrations:  python -m app.db.init_db
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import DEFAULT_CATEGORIES, DEFAULT_SLA_HOURS, Role
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Category, SLARule, User

logger = logging.getLogger(__name__)


def seed_defaults(db: Session) -> None:
    for priority, hours in DEFAULT_SLA_HOURS.items():
        if not db.scalar(select(SLARule).where(SLARule.priority == priority)):
            db.add(SLARule(priority=priority, resolution_hours=hours))

    for name, description in DEFAULT_CATEGORIES:
        if not db.scalar(select(Category).where(func.lower(Category.name) == name.lower())):
            db.add(Category(name=name, description=description))

    if settings.FIRST_ADMIN_EMAIL and settings.FIRST_ADMIN_PASSWORD:
        email = settings.FIRST_ADMIN_EMAIL.lower()
        if not db.scalar(select(User).where(User.email == email)):
            db.add(
                User(
                    email=email,
                    full_name=settings.FIRST_ADMIN_NAME,
                    hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                    role=Role.ADMIN,
                )
            )
            logger.info("Created first admin %s", email)
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_defaults(db)
    print("Seed data ready.")


if __name__ == "__main__":
    main()
