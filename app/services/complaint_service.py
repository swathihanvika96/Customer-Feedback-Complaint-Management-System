from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.constants import AuditAction, ComplaintStatus, Role
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ensure_can_access_complaint, ensure_can_work_complaint, is_manager, is_staff
from app.models import Complaint, ComplaintStatusHistory, User
from app.repositories import agent_repository, complaint_repository, customer_repository
from app.repositories.complaint_repository import ComplaintFilters
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate, StatusChangeRequest
from app.services import audit_service, category_service, customer_service, sla_service, workflow_service
from app.utils.datetime_utils import utcnow
from app.utils.reference_generator import generate_reference

# Statuses that must go through a dedicated endpoint (they need extra data / side effects).
DEDICATED_ENDPOINT_STATUSES = {
    ComplaintStatus.ASSIGNED: "POST /complaints/{id}/assign",
    ComplaintStatus.RESOLVED: "POST /complaints/{id}/resolve",
    ComplaintStatus.CLOSED: "POST /complaints/{id}/close",
    ComplaintStatus.REOPENED: "POST /complaints/{id}/reopen",
}


def _unique_reference(db: Session, now) -> str:
    for _ in range(10):
        ref = generate_reference(now=now)
        if not complaint_repository.reference_exists(db, ref):
            return ref
    raise ConflictError("Could not generate a unique complaint reference, please retry")


def create_complaint(db: Session, user: User, payload: ComplaintCreate) -> Complaint:
    customer = customer_service.resolve_customer_for_actor(db, user, payload.customer_id)
    category_service.get_active_category(db, payload.category_id)
    now = utcnow()
    hours = sla_service.hours_for_priority(db, payload.priority)
    complaint = Complaint(
        reference_no=_unique_reference(db, now),
        customer_id=customer.id,
        category_id=payload.category_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        severity=payload.severity,
        status=ComplaintStatus.OPEN,
        attachment_urls=payload.attachment_urls,
        created_at=now,
        due_at=sla_service.compute_due_at(now, hours),
    )
    db.add(complaint)
    db.flush()
    db.add(ComplaintStatusHistory(complaint_id=complaint.id, from_status=None, to_status=ComplaintStatus.OPEN,
                                  changed_by=user.id, note="Complaint created", created_at=now))
    audit_service.log(db, user.id, AuditAction.COMPLAINT_CREATED, "complaint", complaint.id, {
        "reference_no": complaint.reference_no, "customer_id": customer.id,
        "priority": complaint.priority.value, "due_at": complaint.due_at.isoformat(),
    })
    db.commit()
    return complaint


def get_complaint(db: Session, user: User, complaint_id: int) -> Complaint:
    complaint = complaint_repository.get(db, complaint_id)
    if complaint is None:
        raise NotFoundError("Complaint not found")
    ensure_can_access_complaint(db, user, complaint)
    return complaint


def search_stmt(db: Session, user: User, filters: ComplaintFilters):
    scope_customer = scope_agent = None
    if user.role == Role.CUSTOMER:
        scope_customer = customer_service.get_own_profile(db, user).id
    elif user.role == Role.SUPPORT_AGENT:
        agent = agent_repository.get_by_user_id(db, user.id)
        if agent is None:
            raise ForbiddenError("No agent profile is linked to this account")
        scope_agent = agent.id
    return complaint_repository.search_stmt(
        filters, now=utcnow(), scope_customer_id=scope_customer, scope_agent_id=scope_agent
    )


def update_complaint(db: Session, user: User, complaint_id: int, payload: ComplaintUpdate) -> Complaint:
    complaint = get_complaint(db, user, complaint_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise BadRequestError("No fields to update")
    if complaint.status in (ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED):
        raise ConflictError("Resolved or closed complaints cannot be edited; reopen the complaint first")

    staff_only = {"priority", "severity"}
    if user.role == Role.CUSTOMER:
        if staff_only & changes.keys():
            raise ForbiddenError("Customers cannot change priority or severity")
        if complaint.status != ComplaintStatus.OPEN:
            raise ConflictError("Customers can only edit complaints that are still open")
    elif not is_manager(user):
        ensure_can_work_complaint(db, user, complaint)
        if "priority" in changes:
            raise ForbiddenError("Only managers can change priority")

    if "category_id" in changes:
        category_service.get_active_category(db, changes["category_id"])

    before = {k: (getattr(complaint, k).value if hasattr(getattr(complaint, k), "value") else getattr(complaint, k)) for k in changes}
    for key, value in changes.items():
        setattr(complaint, key, value)
    after = {k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()}

    if "priority" in changes and changes["priority"] != before["priority"]:
        hours = sla_service.hours_for_priority(db, complaint.priority)
        complaint.due_at = sla_service.compute_due_at(complaint.created_at, hours)
        sla_service.reset_sla_markers(complaint)
        after["due_at"] = complaint.due_at.isoformat()

    audit_service.log(db, user.id, AuditAction.COMPLAINT_UPDATED, "complaint", complaint.id, audit_service.diff(before, after))
    db.commit()
    return complaint


def change_status(db: Session, user: User, complaint_id: int, payload: StatusChangeRequest) -> Complaint:
    complaint = get_complaint(db, user, complaint_id)
    if not is_staff(user):
        raise ForbiddenError("Only support staff can change a complaint's status")
    ensure_can_work_complaint(db, user, complaint)
    workflow_service.validate_transition(complaint.status, payload.status)  # 409 on invalid transition
    if payload.status in DEDICATED_ENDPOINT_STATUSES:
        raise BadRequestError(f"Use {DEDICATED_ENDPOINT_STATUSES[payload.status]} to move a complaint to '{payload.status.value}'")
    workflow_service.change_status(db, complaint, payload.status, user, payload.note)
    db.commit()
    return complaint
