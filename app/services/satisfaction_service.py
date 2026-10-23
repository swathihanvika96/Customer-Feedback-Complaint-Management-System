"""Customer satisfaction metrics. Every formula is computed in SQL and documented in FORMULAS."""
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.constants import FINISHED_STATUSES, NEGATIVE_RATING_MAX, POSITIVE_RATING_MIN
from app.models import Category, Complaint, Feedback

FORMULAS = {
    "average_rating": "AVG(rating) over the selected feedback, rounded to 2 decimals; null when there is no feedback.",
    "positive_count": f"COUNT(feedback) with rating >= {POSITIVE_RATING_MIN} (4-5 stars).",
    "neutral_count": f"COUNT(feedback) with {NEGATIVE_RATING_MAX} < rating < {POSITIVE_RATING_MIN} (3 stars).",
    "negative_count": f"COUNT(feedback) with rating <= {NEGATIVE_RATING_MAX} (1-2 stars).",
    "satisfaction_percentage": "CSAT % = positive_count / total_feedback * 100, rounded to 2 decimals; 0 when there is no feedback.",
    "feedback_trends": "Feedback grouped by calendar date (UTC): COUNT(*) and AVG(rating) per day.",
    "resolved_complaint_satisfaction": (
        "Same metrics restricted to feedback linked (complaint_id) to complaints that are resolved or closed. "
        "feedback_response_rate = resolved complaints with feedback / resolved complaints * 100."
    ),
}


def _metrics_columns():
    return (
        func.count(Feedback.id),
        func.avg(Feedback.rating),
        func.coalesce(func.sum(case((Feedback.rating >= POSITIVE_RATING_MIN, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Feedback.rating <= NEGATIVE_RATING_MAX, 1), else_=0)), 0),
    )


def build_summary(total: int, avg, positive: int, negative: int) -> dict:
    total, positive, negative = int(total or 0), int(positive or 0), int(negative or 0)
    return {
        "total_feedback": total,
        "average_rating": round(float(avg), 2) if avg is not None else None,
        "positive_count": positive,
        "neutral_count": total - positive - negative,
        "negative_count": negative,
        "satisfaction_percentage": round(positive / total * 100, 2) if total else 0.0,
    }


def _date_conds(start: datetime | None, end: datetime | None, category_id: int | None = None) -> list:
    conds = []
    if start is not None:
        conds.append(Feedback.feedback_date >= start)
    if end is not None:
        conds.append(Feedback.feedback_date < end)
    if category_id is not None:
        conds.append(Feedback.category_id == category_id)
    return conds


def summary(db: Session, start: datetime | None = None, end: datetime | None = None, category_id: int | None = None) -> dict:
    row = db.execute(select(*_metrics_columns()).where(*_date_conds(start, end, category_id))).one()
    return build_summary(*row)


def by_category(db: Session, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
    rows = db.execute(
        select(Category.id, Category.name, *_metrics_columns())
        .select_from(Feedback)
        .join(Category, Category.id == Feedback.category_id)
        .where(*_date_conds(start, end))
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    ).all()
    result = []
    for cid, name, total, avg, positive, negative in rows:
        s = build_summary(total, avg, positive, negative)
        result.append({
            "category_id": cid, "category_name": name, "total_feedback": s["total_feedback"],
            "average_rating": s["average_rating"], "positive_count": s["positive_count"],
            "negative_count": s["negative_count"], "satisfaction_percentage": s["satisfaction_percentage"],
        })
    return result


def trends(db: Session, start: datetime | None = None, end: datetime | None = None, category_id: int | None = None) -> list[dict]:
    day = func.date(Feedback.feedback_date)
    rows = db.execute(
        select(day, func.count(Feedback.id), func.avg(Feedback.rating))
        .where(*_date_conds(start, end, category_id))
        .group_by(day)
        .order_by(day)
    ).all()
    return [
        {"date": d if not isinstance(d, str) else datetime.strptime(d, "%Y-%m-%d").date(),
         "total_feedback": int(n), "average_rating": round(float(a), 2) if a is not None else None}
        for d, n, a in rows
    ]


def resolved_complaint_satisfaction(db: Session, start: datetime | None = None, end: datetime | None = None) -> dict:
    row = db.execute(
        select(*_metrics_columns())
        .select_from(Feedback)
        .join(Complaint, Complaint.id == Feedback.complaint_id)
        .where(Complaint.status.in_(FINISHED_STATUSES), *_date_conds(start, end))
    ).one()
    data = build_summary(*row)

    resolved_total = db.scalar(select(func.count(Complaint.id)).where(Complaint.status.in_(FINISHED_STATUSES))) or 0
    with_feedback = db.scalar(
        select(func.count(func.distinct(Complaint.id)))
        .select_from(Complaint)
        .join(Feedback, Feedback.complaint_id == Complaint.id)
        .where(Complaint.status.in_(FINISHED_STATUSES))
    ) or 0
    data.update(
        resolved_complaints=int(resolved_total),
        resolved_with_feedback=int(with_feedback),
        feedback_response_rate=round(with_feedback / resolved_total * 100, 2) if resolved_total else 0.0,
    )
    return data
