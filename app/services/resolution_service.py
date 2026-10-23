from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import AuditAction, ComplaintStatus, NotificationType, Role
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import ensure_can_work_complaint, is_manager
from app.models import Complaint, ComplaintResolution, ComplaintStatusHistory, User
from app.repositories import customer_repository, resolution_repository, user_repository
from app.schemas.complaint_resolution import ResolveRequest
from app.services import audit_service, complaint_service, notification_service, sla_service, workflow_service
from app.utils.datetime_utils import utcnow


def _is_owner_customer(db: Session, user: User, complaint: Complaint) -> bool:
    if user.role != Role.CUSTOMER:
        return False
    customer = customer_repository.get_by_user_id(db, user.id)
    return bool(customer and customer.id == complaint.customer_id)


def resolve(db: Session, user: User, complaint_id: int, payload: ResolveRequest) -> ComplaintResolution:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    ensure_can_work_complaint(db, user, complaint)
    workflow_service.validate_transition(complaint.status, ComplaintStatus.RESOLVED)

    resolution = ComplaintResolution(
        complaint_id=complaint.id, resolved_by=user.id, summary=payload.summary,
        root_cause=payload.root_cause, action_taken=payload.action_taken,
    )
    db.add(resolution)
    complaint.resolved_at = utcnow()
    workflow_service.change_status(
        db, complaint, ComplaintStatus.RESOLVED, user, payload.summary[:500],
        audit_action=AuditAction.COMPLAINT_RESOLVED, notify_type=NotificationType.COMPLAINT_RESOLVED,
    )
    db.commit()
    return resolution


def close(db: Session, user: User, complaint_id: int, note: str | None) -> Complaint:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    if not (is_manager(user) or _is_owner_customer(db, user, complaint)):
        # the assigned agent may also close
        if user.role == Role.SUPPORT_AGENT:
            ensure_can_work_complaint(db, user, complaint)
        else:
            raise ForbiddenError("You cannot close this complaint")
    workflow_service.validate_transition(complaint.status, ComplaintStatus.CLOSED)  # must be RESOLVED first
    complaint.closed_at = utcnow()
    workflow_service.change_status(db, complaint, ComplaintStatus.CLOSED, user, note, audit_action=AuditAction.COMPLAINT_CLOSED)
    db.commit()
    return complaint


def reopen(db: Session, user: User, complaint_id: int, reason: str) -> Complaint:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    if not (is_manager(user) or _is_owner_customer(db, user, complaint)):
        raise ForbiddenError("Only the customer who filed the complaint or a manager can reopen it")
    workflow_service.validate_transition(complaint.status, ComplaintStatus.REOPENED)
    now = utcnow()
    if complaint.status == ComplaintStatus.CLOSED and complaint.closed_at:
        deadline = complaint.closed_at + timedelta(days=settings.REOPEN_WINDOW_DAYS)
        if now > deadline:
            raise BadRequestError(
                f"This complaint was closed more than {settings.REOPEN_WINDOW_DAYS} days ago and can no longer be reopened; "
                "please file a new complaint"
            )
    # new SLA cycle
    hours = sla_service.hours_for_priority(db, complaint.priority)
    complaint.due_at = sla_service.compute_due_at(now, hours)
    complaint.resolved_at = None
    complaint.closed_at = None
    complaint.reopen_count += 1
    sla_service.reset_sla_markers(complaint)

    workflow_service.change_status(
        db, complaint, ComplaintStatus.REOPENED, user, reason, audit_action=AuditAction.COMPLAINT_REOPENED, notify=False
    )
    from app.models import SupportAgent

    recipients: set[int | None] = set()
    if complaint.assigned_agent_id:
        agent = db.get(SupportAgent, complaint.assigned_agent_id)
        recipients.add(agent.user_id if agent else None)
    recipients.update(user_repository.active_user_ids_by_roles(db, (Role.SUPPORT_MANAGER,)))
    notification_service.notify(
        db, recipients - {user.id}, NotificationType.STATUS_CHANGED, "Complaint reopened",
        f"Complaint {complaint.reference_no} was reopened: {reason}", complaint.id,
    )
    db.commit()
    return complaint


def get_resolution(db: Session, user: User, complaint_id: int) -> ComplaintResolution:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    resolution = resolution_repository.latest(db, complaint.id)
    if resolution is None:
        raise NotFoundError("This complaint has no resolution yet")
    return resolution


def status_history(db: Session, user: User, complaint_id: int) -> list[ComplaintStatusHistory]:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    return resolution_repository.status_history(db, complaint.id)
