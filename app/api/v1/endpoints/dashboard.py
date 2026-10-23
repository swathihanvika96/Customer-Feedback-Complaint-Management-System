from datetime import date

from fastapi import APIRouter, Depends

from app.dependencies import DbSession, ManagerUser
from app.schemas.common import Page
from app.schemas.dashboard import AgentComplaintCount, DashboardSummary, PriorityCount
from app.services import dashboard_service
from app.utils.pagination import PageParams

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary,
            summary="Totals, open/resolved/overdue, avg resolution time, avg rating (optional date range)")
def summary(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None):
    return dashboard_service.summary(db, date_from, date_to)


@router.get("/complaints-by-priority", response_model=list[PriorityCount])
def complaints_by_priority(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None):
    return dashboard_service.priority_breakdown(db, date_from, date_to)


@router.get("/agent-complaints", response_model=Page[AgentComplaintCount],
            summary="Agent-wise complaint counts (sort_by: agent_name, total, open, resolved, overdue)")
def agent_complaints(
    db: DbSession, manager: ManagerUser, params: PageParams = Depends(),
    date_from: date | None = None, date_to: date | None = None,
):
    return dashboard_service.agent_counts(db, date_from, date_to, params)
