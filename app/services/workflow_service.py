from sqlalchemy.orm import Session

from app.core.constants import AuditAction, ComplaintStatus, NotificationType
from app.core.exceptions import InvalidTransitionError
from app.models import Complaint, ComplaintStatusHistory, Customer, SupportAgent, User
from app.services import audit_service, notification_service

S = ComplaintStatus

ALLOWED_TRANSITIONS: dict[ComplaintStatus, set[ComplaintStatus]] = {
    S.OPEN: {S.ASSIGNED},
    S.ASSIGNED: {S.IN_PROGRESS, S.WAITING_FOR_CUSTOMER},
    S.IN_PROGRESS: {S.WAITING_FOR_CUSTOMER, S.RESOLVED},
    S.WAITING_FOR_CUSTOMER: {S.IN_PROGRESS, S.RESOLVED},
    S.RESOLVED: {S.CLOSED, S.REOPENED},
    S.CLOSED: {S.REOPENED},
    S.REOPENED: {S.ASSIGNED, S.IN_PROGRESS},
}


def can_transition(current: ComplaintStatus, target: ComplaintStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def validate_transition(current: ComplaintStatus, target: ComplaintStatus) -> None:
    if not can_transition(current, target):
        allowed = ", ".join(sorted(s.value for s in ALLOWED_TRANSITIONS.get(current, set()))) or "none"
        raise InvalidTransitionError(
            f"Cannot change status from '{current.value}' to '{target.value}'. Allowed next statuses: {allowed}"
        )


def stakeholder_user_ids(db: Session, complaint: Complaint) -> set[int | None]:
    ids: set[int | None] = set()
    customer = db.get(Customer, complaint.customer_id)
    if customer:
        ids.add(customer.user_id)
    if complaint.assigned_agent_id:
        agent = db.get(SupportAgent, complaint.assigned_agent_id)
        if agent:
            ids.add(agent.user_id)
    return ids


def change_status(
    db: Session,
    complaint: Complaint,
    target: ComplaintStatus,
    actor: User,
    note: str | None = None,
    *,
    audit_action: AuditAction = AuditAction.STATUS_CHANGED,
    notify_type: NotificationType = NotificationType.STATUS_CHANGED,
    notify: bool = True,
) -> None:
    """Validate + apply a transition, record history, audit it and notify stakeholders (no commit)."""
    validate_transition(complaint.status, target)
    previous = complaint.status
    complaint.status = target
    db.add(
        ComplaintStatusHistory(
            complaint_id=complaint.id, from_status=previous, to_status=target, changed_by=actor.id, note=note
        )
    )
    audit_service.log(
        db, actor.id, audit_action, "complaint", complaint.id,
        {"reference_no": complaint.reference_no, "from": previous.value, "to": target.value, "note": note},
    )
    if notify:
        recipients = stakeholder_user_ids(db, complaint) - {actor.id}
        notification_service.notify(
            db, recipients, notify_type, "Complaint status changed",
            f"Complaint {complaint.reference_no} moved from {previous.value} to {target.value}.", complaint.id,
        )
