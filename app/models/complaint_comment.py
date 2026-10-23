from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime_utils import utcnow


class ComplaintComment(Base):
    __tablename__ = "complaint_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(default=False)  # internal notes are hidden from customers
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
