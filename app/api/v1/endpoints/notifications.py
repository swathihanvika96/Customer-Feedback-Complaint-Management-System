from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, DbSession
from app.models import Notification
from app.repositories import notification_repository
from app.schemas.common import MessageOut, Page
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.services import notification_service
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationOut], summary="My notifications (sort_by: created_at)")
def list_notifications(db: DbSession, user: CurrentUser, params: PageParams = Depends(), unread_only: bool = False):
    stmt = notification_repository.list_stmt(user.id, unread_only)
    stmt = apply_sorting(stmt, {"created_at": Notification.created_at}, params.sort_by, params.sort_order,
                         "created_at", Notification.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.get("/unread-count", response_model=UnreadCountOut)
def unread_count(db: DbSession, user: CurrentUser):
    return {"unread": notification_repository.unread_count(db, user.id)}


@router.post("/read-all", response_model=MessageOut)
def read_all(db: DbSession, user: CurrentUser):
    count = notification_service.mark_all_read(db, user)
    return {"message": f"{count} notification(s) marked as read"}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: DbSession, user: CurrentUser):
    return notification_service.mark_read(db, user, notification_id)
