from sqlalchemy.orm import Session

from app.core.constants import AuditAction, Role
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import is_manager
from app.core.security import hash_password
from app.models import SupportAgent, User
from app.repositories import agent_repository, user_repository
from app.schemas.support_agent import AgentCreate, AgentUpdate, AgentWorkloadOut
from app.services import audit_service, auth_service
from app.core.constants import ACTIVE_STATUSES


def create_agent(db: Session, actor: User, payload: AgentCreate) -> SupportAgent:
    if user_repository.get_by_email(db, payload.email):
        raise ConflictError("Email is already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=Role.SUPPORT_AGENT,
    )
    db.add(user)
    db.flush()
    agent = SupportAgent(user_id=user.id, department=payload.department, max_workload=payload.max_workload)
    db.add(agent)
    db.flush()
    audit_service.log(db, actor.id, AuditAction.USER_CREATED, "support_agent", agent.id, {"email": user.email})
    db.commit()
    return agent


def get_agent(db: Session, agent_id: int) -> SupportAgent:
    agent = agent_repository.get(db, agent_id)
    if agent is None:
        raise NotFoundError("Support agent not found")
    return agent


def ensure_can_view_agent(db: Session, user: User, agent: SupportAgent) -> None:
    if is_manager(user) or agent.user_id == user.id:
        return
    raise ForbiddenError("Agents can only view their own workload")


def update_agent(db: Session, agent_id: int, payload: AgentUpdate) -> SupportAgent:
    agent = get_agent(db, agent_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    db.commit()
    return agent


def set_active(db: Session, actor: User, agent_id: int, active: bool) -> SupportAgent:
    agent = get_agent(db, agent_id)
    agent.is_active = active
    agent.user.is_active = active
    if not active:
        auth_service.revoke_all_tokens(db, agent.user_id)
    audit_service.log(
        db, actor.id, AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED, "support_agent", agent.id
    )
    db.commit()
    return agent


def workload(db: Session, agent: SupportAgent) -> AgentWorkloadOut:
    by_status = agent_repository.status_counts(db, agent.id)
    active = sum(by_status.get(s.value, 0) for s in ACTIVE_STATUSES)
    return AgentWorkloadOut(
        agent_id=agent.id,
        agent_name=agent.full_name,
        max_workload=agent.max_workload,
        active_complaints=active,
        available_capacity=max(agent.max_workload - active, 0),
        by_status=by_status,
    )
