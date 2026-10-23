from datetime import date

from sqlalchemy.orm import Session

from app.repositories import dashboard_repository
from app.services import satisfaction_service
from app.utils.datetime_utils import day_bounds
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting


def satisfaction_summary(db: Session, date_from: date | None, date_to: date | None, category_id: int | None):
    start, end = day_bounds(date_from, date_to)
    return satisfaction_service.summary(db, start, end, category_id)


def satisfaction_by_category(db: Session, date_from: date | None, date_to: date | None):
    start, end = day_bounds(date_from, date_to)
    return satisfaction_service.by_category(db, start, end)


def satisfaction_trends(db: Session, date_from: date | None, date_to: date | None, category_id: int | None):
    start, end = day_bounds(date_from, date_to)
    return satisfaction_service.trends(db, start, end, category_id)


def resolved_satisfaction(db: Session, date_from: date | None, date_to: date | None):
    start, end = day_bounds(date_from, date_to)
    return satisfaction_service.resolved_complaint_satisfaction(db, start, end)


def complaints_by_category(db: Session, date_from: date | None, date_to: date | None) -> list[dict]:
    start, end = day_bounds(date_from, date_to)
    return [
        {"category_id": cid, "category_name": name, "total": int(t), "open": int(o), "resolved": int(r)}
        for cid, name, t, o, r in dashboard_repository.complaints_by_category(db, start, end)
    ]


def agent_performance(db: Session, date_from: date | None, date_to: date | None, params: PageParams) -> dict:
    start, end = day_bounds(date_from, date_to)
    stmt = dashboard_repository.agent_performance(db, start, end)
    cols = {c.key: c for c in stmt.selected_columns}
    stmt = apply_sorting(stmt, {"agent_name": cols["agent_name"], "assigned": cols["assigned"],
                                "resolved": cols["resolved"], "avg_hours": cols["avg_hours"]},
                         params.sort_by, params.sort_order, default="resolved")
    rows, total = paginate(db, stmt, params, scalars=False)
    items = [
        {"agent_id": r.agent_id, "agent_name": r.agent_name, "assigned": int(r.assigned), "resolved": int(r.resolved),
         "average_resolution_hours": round(float(r.avg_hours), 2) if r.avg_hours is not None else None}
        for r in rows
    ]
    return make_page(items, total, params)
