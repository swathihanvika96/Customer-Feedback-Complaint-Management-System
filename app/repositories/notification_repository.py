from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.models import Notification


def get(db: Session, notification_id: int) -> Notification | None:
    return db.get(Notification, notification_id)


def list_stmt(user_id: int, unread_only: bool = False) -> Select:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return stmt


def unread_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read.is_(False))
    ) or 0


def mark_all_read(db: Session, user_id: int) -> int:
    result = db.execute(
        update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values(is_read=True)
    )
    return result.rowcount or 0
