from datetime import date

from fastapi import APIRouter, Depends

from app.dependencies import DbSession, ManagerUser
from app.schemas.common import Page
from app.schemas.reports import (
    AgentPerformance, CategorySatisfaction, ComplaintsByCategory,
    ResolvedComplaintSatisfaction, SatisfactionSummary, TrendPoint,
)
from app.services import report_service, satisfaction_service
from app.utils.pagination import PageParams

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/satisfaction/formulas", response_model=dict[str, str], summary="How every satisfaction metric is calculated")
def formulas(manager: ManagerUser):
    return satisfaction_service.FORMULAS


@router.get("/satisfaction", response_model=SatisfactionSummary)
def satisfaction(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None,
                 category_id: int | None = None):
    return report_service.satisfaction_summary(db, date_from, date_to, category_id)


@router.get("/satisfaction/categories", response_model=list[CategorySatisfaction])
def satisfaction_by_category(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None):
    return report_service.satisfaction_by_category(db, date_from, date_to)


@router.get("/satisfaction/trends", response_model=list[TrendPoint])
def satisfaction_trends(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None,
                        category_id: int | None = None):
    return report_service.satisfaction_trends(db, date_from, date_to, category_id)


@router.get("/satisfaction/resolved-complaints", response_model=ResolvedComplaintSatisfaction)
def resolved_complaint_satisfaction(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None):
    return report_service.resolved_satisfaction(db, date_from, date_to)


@router.get("/complaints-by-category", response_model=list[ComplaintsByCategory])
def complaints_by_category(db: DbSession, manager: ManagerUser, date_from: date | None = None, date_to: date | None = None):
    return report_service.complaints_by_category(db, date_from, date_to)


@router.get("/agent-performance", response_model=Page[AgentPerformance],
            summary="Per-agent assigned/resolved counts and avg resolution hours (sort_by: agent_name, assigned, resolved, avg_hours)")
def agent_performance(db: DbSession, manager: ManagerUser, params: PageParams = Depends(),
                      date_from: date | None = None, date_to: date | None = None):
    return report_service.agent_performance(db, date_from, date_to, params)
