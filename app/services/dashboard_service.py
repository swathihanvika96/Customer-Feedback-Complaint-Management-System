from datetime import date

from sqlalchemy.orm import Session

from app.repositories import dashboard_repository
from app.schemas.dashboard import DashboardSummary
from app.utils.datetime_utils import day_bounds, utcnow
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting


def summary(db: Session, date_from: date | None, date_to: date | None) -> DashboardSummary:
    start, end = day_bounds(date_from, date_to)
    data = dashboard_repository.summary(db, start, end, utcnow())
    return DashboardSummary(
        date_from=date_from, date_to=date_to,
        complaints_by_priority=dashboard_repository.complaints_by_priority(db, start, end),
        **data,
    )


def priority_breakdown(db: Session, date_from: date | None, date_to: date | None) -> list[dict]:
    start, end = day_bounds(date_from, date_to)
    return dashboard_repository.complaints_by_priority(db, start, end)


def agent_counts(db: Session, date_from: date | None, date_to: date | None, params: PageParams) -> dict:
    start, end = day_bounds(date_from, date_to)
    stmt, sort_columns = dashboard_repository.agent_counts_stmt(start, end, utcnow())
    stmt = apply_sorting(stmt, sort_columns, params.sort_by, params.sort_order, default="total")
    rows, total = paginate(db, stmt, params, scalars=False)
    items = [
        {"agent_id": r.agent_id, "agent_name": r.agent_name, "total": int(r.total),
         "open": int(r.open), "resolved": int(r.resolved), "overdue": int(r.overdue)}
        for r in rows
    ]
    return make_page(items, total, params)
