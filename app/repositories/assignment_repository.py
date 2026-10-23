from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplaintAssignment


def get_active(db: Session, complaint_id: int) -> ComplaintAssignment | None:
    return db.scalar(
        select(ComplaintAssignment).where(
            ComplaintAssignment.complaint_id == complaint_id, ComplaintAssignment.is_active.is_(True)
        )
    )


def history(db: Session, complaint_id: int) -> list[ComplaintAssignment]:
    return list(
        db.scalars(
            select(ComplaintAssignment)
            .where(ComplaintAssignment.complaint_id == complaint_id)
            .order_by(ComplaintAssignment.assigned_at, ComplaintAssignment.id)
        ).all()
    )
