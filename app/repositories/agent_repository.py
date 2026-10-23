from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ACTIVE_STATUSES
from app.models import Complaint, SupportAgent, User
from app.utils.filtering import text_search


def get(db: Session, agent_id: int) -> SupportAgent | None:
    return db.get(SupportAgent, agent_id)


def get_by_user_id(db: Session, user_id: int) -> SupportAgent | None:
    return db.scalar(select(SupportAgent).where(SupportAgent.user_id == user_id))


def list_stmt(is_active: bool | None = None, q: str | None = None, department: str | None = None) -> Select:
    stmt = select(SupportAgent).join(User, User.id == SupportAgent.user_id).options(joinedload(SupportAgent.user))
    if is_active is not None:
        stmt = stmt.where(SupportAgent.is_active == is_active)
    if department:
        stmt = stmt.where(SupportAgent.department.ilike(department))
    cond = text_search([User.full_name, User.email], q)
    if cond is not None:
        stmt = stmt.where(cond)
    return stmt


def status_counts(db: Session, agent_id: int) -> dict[str, int]:
    rows = db.execute(
        select(Complaint.status, func.count(Complaint.id))
        .where(Complaint.assigned_agent_id == agent_id)
        .group_by(Complaint.status)
    ).all()
    return {status.value: count for status, count in rows}


def active_count(db: Session, agent_id: int) -> int:
    return db.scalar(
        select(func.count(Complaint.id)).where(
            Complaint.assigned_agent_id == agent_id, Complaint.status.in_(ACTIVE_STATUSES)
        )
    ) or 0
