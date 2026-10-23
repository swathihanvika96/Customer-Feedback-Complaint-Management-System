from fastapi import APIRouter, Depends, Query, status

from app.core.constants import Role
from app.core.exceptions import ForbiddenError
from app.core.permissions import is_manager
from app.dependencies import CurrentUser, DbSession, ManagerUser, StaffUser
from app.models import SupportAgent, User
from app.repositories import agent_repository, complaint_repository
from app.repositories.complaint_repository import SORT_COLUMNS, ComplaintFilters
from app.schemas.common import Page
from app.schemas.complaint import ComplaintOut
from app.schemas.support_agent import AgentCreate, AgentOut, AgentUpdate, AgentWorkloadOut
from app.services import agent_service
from app.utils.datetime_utils import utcnow
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting
from app.models import Complaint

router = APIRouter(prefix="/agents", tags=["Support Agents"])


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED, summary="Create a support agent (manager)")
def create_agent(payload: AgentCreate, db: DbSession, manager: ManagerUser):
    return agent_service.create_agent(db, manager, payload)


@router.get("", response_model=Page[AgentOut], summary="List agents (sort_by: created_at, name, department)")
def list_agents(
    db: DbSession, staff: StaffUser, params: PageParams = Depends(),
    is_active: bool | None = None, department: str | None = None, q: str | None = Query(None),
):
    stmt = agent_repository.list_stmt(is_active, q, department)
    stmt = apply_sorting(stmt, {"created_at": SupportAgent.created_at, "name": User.full_name,
                                "department": SupportAgent.department}, params.sort_by, params.sort_order,
                         "created_at", SupportAgent.id)
    items, total = paginate(db, stmt, params)
    items = list({a.id: a for a in items}.values())
    return make_page(items, total, params)


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: DbSession, staff: StaffUser):
    return agent_service.get_agent(db, agent_id)


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: int, payload: AgentUpdate, db: DbSession, manager: ManagerUser):
    return agent_service.update_agent(db, agent_id, payload)


@router.post("/{agent_id}/activate", response_model=AgentOut)
def activate_agent(agent_id: int, db: DbSession, manager: ManagerUser):
    return agent_service.set_active(db, manager, agent_id, True)


@router.post("/{agent_id}/deactivate", response_model=AgentOut)
def deactivate_agent(agent_id: int, db: DbSession, manager: ManagerUser):
    return agent_service.set_active(db, manager, agent_id, False)


@router.get("/{agent_id}/workload", response_model=AgentWorkloadOut, summary="Agent workload")
def agent_workload(agent_id: int, db: DbSession, user: StaffUser):
    agent = agent_service.get_agent(db, agent_id)
    agent_service.ensure_can_view_agent(db, user, agent)
    return agent_service.workload(db, agent)


@router.get("/{agent_id}/complaints", response_model=Page[ComplaintOut], summary="Complaints assigned to an agent")
def agent_complaints(agent_id: int, db: DbSession, user: StaffUser, params: PageParams = Depends()):
    agent = agent_service.get_agent(db, agent_id)
    agent_service.ensure_can_view_agent(db, user, agent)
    stmt = complaint_repository.search_stmt(ComplaintFilters(agent_id=agent.id), now=utcnow())
    stmt = apply_sorting(stmt, SORT_COLUMNS, params.sort_by, params.sort_order, "created_at", Complaint.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)
