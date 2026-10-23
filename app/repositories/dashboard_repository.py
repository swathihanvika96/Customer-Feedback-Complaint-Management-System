from datetime import datetime

from sqlalchemy import Select, case, func, literal_column, select
from sqlalchemy.orm import Session

from app.core.constants import ACTIVE_STATUSES, FINISHED_STATUSES, Priority
from app.models import Complaint, Customer, Feedback, SupportAgent, User


def _range(col, start: datetime | None, end: datetime | None) -> list:
    conds = []
    if start is not None:
        conds.append(col >= start)
    if end is not None:
        conds.append(col < end)
    return conds


def duration_hours_expr(db: Session):
    """Dialect-specific (resolved_at - created_at) in hours, computed inside the database."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        return (func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at)) * 24.0
    if dialect in ("mysql", "mariadb"):
        return func.timestampdiff(literal_column("SECOND"), Complaint.created_at, Complaint.resolved_at) / 3600.0
    return func.extract("epoch", Complaint.resolved_at - Complaint.created_at) / 3600.0


def _round(value, digits: int = 2):
    return round(float(value), digits) if value is not None else None


def summary(db: Session, start: datetime | None, end: datetime | None, now: datetime) -> dict:
    total_customers = db.scalar(select(func.count(Customer.id)).where(*_range(Customer.created_at, start, end))) or 0
    total_feedback = db.scalar(select(func.count(Feedback.id)).where(*_range(Feedback.feedback_date, start, end))) or 0
    avg_rating = db.scalar(select(func.avg(Feedback.rating)).where(*_range(Feedback.feedback_date, start, end)))

    active = Complaint.status.in_(ACTIVE_STATUSES)
    row = db.execute(
        select(
            func.count(Complaint.id),
            func.coalesce(func.sum(case((active, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Complaint.status.in_(FINISHED_STATUSES), 1), else_=0)), 0),
            func.coalesce(func.sum(case((active & (Complaint.due_at < now), 1), else_=0)), 0),
        ).where(*_range(Complaint.created_at, start, end))
    ).one()

    avg_hours = db.scalar(
        select(func.avg(duration_hours_expr(db))).where(
            Complaint.resolved_at.is_not(None), *_range(Complaint.created_at, start, end)
        )
    )
    return {
        "total_customers": int(total_customers),
        "total_feedback": int(total_feedback),
        "total_complaints": int(row[0]),
        "open_complaints": int(row[1]),
        "resolved_complaints": int(row[2]),
        "overdue_complaints": int(row[3]),
        "average_resolution_hours": _round(avg_hours),
        "average_customer_rating": _round(avg_rating),
    }


def complaints_by_priority(db: Session, start: datetime | None, end: datetime | None) -> list[dict]:
    rows = db.execute(
        select(Complaint.priority, func.count(Complaint.id))
        .where(*_range(Complaint.created_at, start, end))
        .group_by(Complaint.priority)
    ).all()
    counts = {p.value: c for p, c in rows}
    return [{"priority": p.value, "count": int(counts.get(p.value, 0))} for p in (Priority.HIGH, Priority.MEDIUM, Priority.LOW)]


def agent_counts_stmt(start: datetime | None, end: datetime | None, now: datetime) -> tuple[Select, dict]:
    """Agent-wise counts (agents with zero complaints included via LEFT JOIN)."""
    active = Complaint.status.in_(ACTIVE_STATUSES)
    total = func.count(Complaint.id).label("total")
    open_ = func.coalesce(func.sum(case((active, 1), else_=0)), 0).label("open")
    resolved = func.coalesce(func.sum(case((Complaint.status.in_(FINISHED_STATUSES), 1), else_=0)), 0).label("resolved")
    overdue = func.coalesce(func.sum(case((active & (Complaint.due_at < now), 1), else_=0)), 0).label("overdue")
    name = User.full_name.label("agent_name")

    join_cond = Complaint.assigned_agent_id == SupportAgent.id
    for c in _range(Complaint.created_at, start, end):
        join_cond = join_cond & c

    stmt = (
        select(SupportAgent.id.label("agent_id"), name, total, open_, resolved, overdue)
        .select_from(SupportAgent)
        .join(User, User.id == SupportAgent.user_id)
        .outerjoin(Complaint, join_cond)
        .group_by(SupportAgent.id, User.full_name)
    )
    sort_columns = {"agent_name": name, "total": total, "open": open_, "resolved": resolved, "overdue": overdue}
    return stmt, sort_columns


def agent_performance(db: Session, start: datetime | None, end: datetime | None) -> Select:
    assigned = func.count(Complaint.id).label("assigned")
    resolved = func.coalesce(func.sum(case((Complaint.resolved_at.is_not(None), 1), else_=0)), 0).label("resolved")
    avg_hours = func.avg(case((Complaint.resolved_at.is_not(None), duration_hours_expr(db)))).label("avg_hours")
    join_cond = Complaint.assigned_agent_id == SupportAgent.id
    for c in _range(Complaint.created_at, start, end):
        join_cond = join_cond & c
    return (
        select(SupportAgent.id.label("agent_id"), User.full_name.label("agent_name"), assigned, resolved, avg_hours)
        .select_from(SupportAgent)
        .join(User, User.id == SupportAgent.user_id)
        .outerjoin(Complaint, join_cond)
        .group_by(SupportAgent.id, User.full_name)
    )


def complaints_by_category(db: Session, start: datetime | None, end: datetime | None):
    from app.models import Category

    active = Complaint.status.in_(ACTIVE_STATUSES)
    return db.execute(
        select(
            Category.id,
            Category.name,
            func.count(Complaint.id),
            func.coalesce(func.sum(case((active, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Complaint.status.in_(FINISHED_STATUSES), 1), else_=0)), 0),
        )
        .select_from(Complaint)
        .join(Category, Category.id == Complaint.category_id)
        .where(*_range(Complaint.created_at, start, end))
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    ).all()
