from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplaintComment


def list_for_complaint(db: Session, complaint_id: int, include_internal: bool) -> list[ComplaintComment]:
    stmt = select(ComplaintComment).where(ComplaintComment.complaint_id == complaint_id)
    if not include_internal:
        stmt = stmt.where(ComplaintComment.is_internal.is_(False))
    return list(db.scalars(stmt.order_by(ComplaintComment.created_at, ComplaintComment.id)).all())
