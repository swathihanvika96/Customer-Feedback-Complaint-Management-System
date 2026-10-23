from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FeedbackStatus
from app.db.base import Base, enum_column
from app.utils.datetime_utils import utcnow


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating_range"),
        # one feedback per (customer, complaint); NULL complaint_id (general feedback) is unaffected
        UniqueConstraint("customer_id", "complaint_id", name="uq_feedback_customer_complaint"),
        Index("ix_feedback_category_date", "category_id", "feedback_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    complaint_id: Mapped[Optional[int]] = mapped_column(ForeignKey("complaints.id"), nullable=True, index=True)
    rating: Mapped[int] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[FeedbackStatus] = mapped_column(enum_column(FeedbackStatus), default=FeedbackStatus.SUBMITTED, index=True)
    feedback_date: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
