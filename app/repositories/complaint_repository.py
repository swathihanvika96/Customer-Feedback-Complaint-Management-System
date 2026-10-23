from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, case, select
from sqlalchemy.orm import Session

from app.core.constants import ACTIVE_STATUSES, ComplaintStatus, Priority
from app.models import Complaint
from app.utils.filtering import text_search


@dataclass
class ComplaintFilters:
    status: ComplaintStatus | None = None
    priority: Priority | None = None
    category_id: int | None = None
    agent_id: int | None = None
    customer_id: int | None = None
    created_start: datetime | None = None
    created_end: datetime | None = None  # exclusive
    resolved_start: datetime | None = None
    resolved_end: datetime | None = None  # exclusive
    q: str | None = None
    overdue: bool | None = None


PRIORITY_RANK = case(
    (Complaint.priority == Priority.HIGH, 3),
    (Complaint.priority == Priority.MEDIUM, 2),
    else_=1,
)

SORT_COLUMNS = {
    "created_at": Complaint.created_at,
    "updated_at": Complaint.updated_at,
    "due_at": Complaint.due_at,
    "resolved_at": Complaint.resolved_at,
    "status": Complaint.status,
    "priority": PRIORITY_RANK,
    "reference_no": Complaint.reference_no,
}


def get(db: Session, complaint_id: int) -> Complaint | None:
    return db.get(Complaint, complaint_id)


def reference_exists(db: Session, reference: str) -> bool:
    return db.scalar(select(Complaint.id).where(Complaint.reference_no == reference)) is not None


def search_stmt(
    filters: ComplaintFilters,
    *,
    now: datetime,
    scope_customer_id: int | None = None,
    scope_agent_id: int | None = None,
) -> Select:
    """One SELECT with all filters pushed into SQL; callers paginate with LIMIT/OFFSET."""
    stmt = select(Complaint)
    conds = []
    if scope_customer_id is not None:
        conds.append(Complaint.customer_id == scope_customer_id)
    if scope_agent_id is not None:
        conds.append(Complaint.assigned_agent_id == scope_agent_id)
    if filters.status:
        conds.append(Complaint.status == filters.status)
    if filters.priority:
        conds.append(Complaint.priority == filters.priority)
    if filters.category_id is not None:
        conds.append(Complaint.category_id == filters.category_id)
    if filters.agent_id is not None:
        conds.append(Complaint.assigned_agent_id == filters.agent_id)
    if filters.customer_id is not None:
        conds.append(Complaint.customer_id == filters.customer_id)
    if filters.created_start:
        conds.append(Complaint.created_at >= filters.created_start)
    if filters.created_end:
        conds.append(Complaint.created_at < filters.created_end)
    if filters.resolved_start:
        conds.append(Complaint.resolved_at >= filters.resolved_start)
    if filters.resolved_end:
        conds.append(Complaint.resolved_at < filters.resolved_end)
    if filters.overdue is True:
        conds.append(Complaint.status.in_(ACTIVE_STATUSES))
        conds.append(Complaint.due_at < now)
    cond = text_search([Complaint.reference_no, Complaint.title, Complaint.description], filters.q)
    if cond is not None:
        conds.append(cond)
    return stmt.where(*conds) if conds else stmt


def overdue_stmt(now: datetime, scope_agent_id: int | None = None) -> Select:
    stmt = select(Complaint).where(Complaint.status.in_(ACTIVE_STATUSES), Complaint.due_at < now)
    if scope_agent_id is not None:
        stmt = stmt.where(Complaint.assigned_agent_id == scope_agent_id)
    return stmt
