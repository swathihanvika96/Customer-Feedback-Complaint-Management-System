from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplaintResolution, ComplaintStatusHistory


def latest(db: Session, complaint_id: int) -> ComplaintResolution | None:
    return db.scalar(
        select(ComplaintResolution)
        .where(ComplaintResolution.complaint_id == complaint_id)
        .order_by(ComplaintResolution.created_at.desc(), ComplaintResolution.id.desc())
        .limit(1)
    )


def status_history(db: Session, complaint_id: int) -> list[ComplaintStatusHistory]:
    return list(
        db.scalars(
            select(ComplaintStatusHistory)
            .where(ComplaintStatusHistory.complaint_id == complaint_id)
            .order_by(ComplaintStatusHistory.created_at, ComplaintStatusHistory.id)
        ).all()
    )
