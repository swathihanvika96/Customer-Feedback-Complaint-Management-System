from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.constants import FeedbackStatus
from app.models import Feedback
from app.utils.filtering import text_search


def get(db: Session, feedback_id: int) -> Feedback | None:
    return db.get(Feedback, feedback_id)


def get_for_complaint(db: Session, customer_id: int, complaint_id: int) -> Feedback | None:
    return db.scalar(select(Feedback).where(Feedback.customer_id == customer_id, Feedback.complaint_id == complaint_id))


def find_recent_duplicate(
    db: Session, customer_id: int, category_id: int, rating: int, description: str, since: datetime
) -> Feedback | None:
    return db.scalar(
        select(Feedback).where(
            Feedback.customer_id == customer_id,
            Feedback.category_id == category_id,
            Feedback.rating == rating,
            Feedback.description == description,
            Feedback.feedback_date >= since,
        )
    )


def search_stmt(
    *,
    customer_id: int | None = None,
    category_id: int | None = None,
    status: FeedbackStatus | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    q: str | None = None,
) -> Select:
    stmt = select(Feedback)
    if customer_id is not None:
        stmt = stmt.where(Feedback.customer_id == customer_id)
    if category_id is not None:
        stmt = stmt.where(Feedback.category_id == category_id)
    if status is not None:
        stmt = stmt.where(Feedback.status == status)
    if rating_min is not None:
        stmt = stmt.where(Feedback.rating >= rating_min)
    if rating_max is not None:
        stmt = stmt.where(Feedback.rating <= rating_max)
    if start is not None:
        stmt = stmt.where(Feedback.feedback_date >= start)
    if end is not None:
        stmt = stmt.where(Feedback.feedback_date < end)
    cond = text_search([Feedback.description], q)
    if cond is not None:
        stmt = stmt.where(cond)
    return stmt
