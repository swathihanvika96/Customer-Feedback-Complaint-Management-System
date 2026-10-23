from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ComplaintStatus
from app.db.base import Base, enum_column
from app.utils.datetime_utils import utcnow


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    from_status: Mapped[Optional[ComplaintStatus]] = mapped_column(enum_column(ComplaintStatus), nullable=True)
    to_status: Mapped[ComplaintStatus] = mapped_column(enum_column(ComplaintStatus))
    changed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
