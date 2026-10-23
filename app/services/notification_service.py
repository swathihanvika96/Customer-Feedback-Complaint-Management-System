from typing import Iterable

from fastapi import status  # noqa: F401
from sqlalchemy.orm import Session

from app.core.constants import NotificationType
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import Notification, User
from app.repositories import notification_repository


def notify(
    db: Session,
    user_ids: Iterable[int | None],
    type_: NotificationType,
    title: str,
    message: str,
    complaint_id: int | None = None,
) -> int:
    ids = {uid for uid in user_ids if uid is not None}
    for uid in ids:
        db.add(Notification(user_id=uid, type=type_, title=title, message=message, complaint_id=complaint_id))
    return len(ids)


def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    notification = notification_repository.get(db, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")
    if notification.user_id != user.id:
        raise ForbiddenError("You can only access your own notifications")
    notification.is_read = True
    db.commit()
    return notification


def mark_all_read(db: Session, user: User) -> int:
    count = notification_repository.mark_all_read(db, user.id)
    db.commit()
    return count
