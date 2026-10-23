from fastapi import APIRouter, Depends

from app.core.constants import Priority, Role
from app.core.permissions import is_manager
from app.dependencies import CurrentUser, DbSession, ManagerUser, StaffUser
from app.models import Complaint
from app.repositories import agent_repository
from app.schemas.common import Page
from app.schemas.sla import SLACheckResult, SLARuleOut, SLARuleUpdate, SLAStatusOut
from app.services import complaint_service, sla_service
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/sla", tags=["SLA"])


@router.get("/rules", response_model=list[SLARuleOut])
def list_rules(db: DbSession, user: CurrentUser):
    return sla_service.get_rules(db)


@router.put("/rules/{priority}", response_model=SLARuleOut, summary="Change the SLA hours of a priority (manager)")
def update_rule(priority: Priority, payload: SLARuleUpdate, db: DbSession, manager: ManagerUser):
    return sla_service.update_rule(db, manager, priority, payload.resolution_hours)


@router.get("/overdue", response_model=Page[SLAStatusOut], summary="Overdue complaints (sort_by: due_at, created_at)")
def overdue_complaints(db: DbSession, user: StaffUser, params: PageParams = Depends()):
    scope_agent = None
    if user.role == Role.SUPPORT_AGENT:
        agent = agent_repository.get_by_user_id(db, user.id)
        scope_agent = agent.id if agent else -1
    stmt = sla_service.overdue_stmt(scope_agent_id=scope_agent)
    stmt = apply_sorting(stmt, {"due_at": Complaint.due_at, "created_at": Complaint.created_at},
                         params.sort_by, params.sort_order, "due_at", Complaint.id)
    items, total = paginate(db, stmt, params)
    return make_page([sla_service.evaluate(c) for c in items], total, params)


@router.get("/complaints/{complaint_id}", response_model=SLAStatusOut,
            summary="SLA status: time remaining, breach state, resolution duration")
def complaint_sla(complaint_id: int, db: DbSession, user: CurrentUser):
    return sla_service.evaluate(complaint_service.get_complaint(db, user, complaint_id))


@router.post("/check", response_model=SLACheckResult,
             summary="Generate SLA 'approaching' / 'breached' notifications (call from a cron job)")
def run_check(db: DbSession, manager: ManagerUser):
    return sla_service.run_check(db)
