from pydantic import BaseModel

from app.core.constants import NotificationType
from app.schemas.common import ORMModel, UTCDateTime


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    title: str
    message: str
    complaint_id: int | None
    is_read: bool
    created_at: UTCDateTime


class UnreadCountOut(BaseModel):
    unread: int
