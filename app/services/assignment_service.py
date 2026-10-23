from sqlalchemy.orm import Session

from app.core.constants import FINISHED_STATUSES, AuditAction, ComplaintStatus, NotificationType
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Complaint, ComplaintAssignment, SupportAgent, User
from app.repositories import agent_repository, assignment_repository, complaint_repository
from app.services import audit_service, notification_service, workflow_service
from app.utils.datetime_utils import utcnow


def _load_complaint(db: Session, complaint_id: int) -> Complaint:
    complaint = complaint_repository.get(db, complaint_id)
    if complaint is None:
        raise NotFoundError("Complaint not found")
    return complaint


def _load_assignable_agent(db: Session, agent_id: int) -> SupportAgent:
    agent = agent_repository.get(db, agent_id)
    if agent is None:
        raise NotFoundError("Support agent not found")
    if not agent.is_active or not agent.user.is_active:
        raise BadRequestError("Support agent is deactivated")
    if agent_repository.active_count(db, agent.id) >= agent.max_workload:
        raise ConflictError(f"Agent {agent.full_name} is at full capacity ({agent.max_workload} active complaints)")
    return agent


def _notify_agent(db: Session, agent: SupportAgent, complaint: Complaint, actor: User, verb: str) -> None:
    notification_service.notify(
        db, {agent.user_id} - {actor.id}, NotificationType.COMPLAINT_ASSIGNED, "Complaint assigned",
        f"Complaint {complaint.reference_no} was {verb} to you.", complaint.id,
    )


def assign(db: Session, manager: User, complaint_id: int, agent_id: int, reason: str | None) -> Complaint:
    complaint = _load_complaint(db, complaint_id)
    if complaint.status not in (ComplaintStatus.OPEN, ComplaintStatus.REOPENED):
        raise ConflictError(
            f"Only open or reopened complaints can be assigned (current status: {complaint.status.value}). "
            "Use /reassign to change the agent of an active complaint."
        )
    agent = _load_assignable_agent(db, agent_id)

    current = assignment_repository.get_active(db, complaint.id)
    if current:  # a reopened complaint may still carry its previous assignment
        current.is_active, current.unassigned_at = False, utcnow()

    db.add(ComplaintAssignment(complaint_id=complaint.id, agent_id=agent.id, assigned_by=manager.id, reason=reason))
    complaint.assigned_agent_id = agent.id
    audit_service.log(db, manager.id, AuditAction.AGENT_ASSIGNED, "complaint", complaint.id,
                      {"reference_no": complaint.reference_no, "agent_id": agent.id, "reason": reason})
    workflow_service.change_status(db, complaint, ComplaintStatus.ASSIGNED, manager,
                                   f"Assigned to {agent.full_name}", audit_action=AuditAction.STATUS_CHANGED, notify=False)
    _notify_agent(db, agent, complaint, manager, "assigned")
    # let the customer know their complaint now has an owner
    db.flush()
    notification_service.notify(
        db, workflow_service.stakeholder_user_ids(db, complaint) - {manager.id, agent.user_id},
        NotificationType.STATUS_CHANGED, "Complaint status changed",
        f"Complaint {complaint.reference_no} is now assigned.", complaint.id,
    )
    db.commit()
    return complaint


def reassign(db: Session, manager: User, complaint_id: int, agent_id: int, reason: str | None) -> Complaint:
    complaint = _load_complaint(db, complaint_id)
    current = assignment_repository.get_active(db, complaint.id)
    if current is None or complaint.status == ComplaintStatus.OPEN:
        raise ConflictError("Complaint has no current assignment; use /assign instead")
    if complaint.status in FINISHED_STATUSES:
        raise ConflictError("Resolved or closed complaints cannot be reassigned")
    if current.agent_id == agent_id:
        raise BadRequestError("Complaint is already assigned to this agent")
    new_agent = _load_assignable_agent(db, agent_id)
    old_agent = agent_repository.get(db, current.agent_id)

    current.is_active, current.unassigned_at = False, utcnow()
    db.add(ComplaintAssignment(complaint_id=complaint.id, agent_id=new_agent.id, assigned_by=manager.id, reason=reason))
    complaint.assigned_agent_id = new_agent.id
    audit_service.log(db, manager.id, AuditAction.AGENT_REASSIGNED, "complaint", complaint.id, {
        "reference_no": complaint.reference_no, "from_agent_id": current.agent_id,
        "to_agent_id": new_agent.id, "reason": reason,
    })
    _notify_agent(db, new_agent, complaint, manager, "reassigned")
    if old_agent:
        notification_service.notify(
            db, {old_agent.user_id} - {manager.id}, NotificationType.COMPLAINT_ASSIGNED, "Complaint reassigned",
            f"Complaint {complaint.reference_no} was reassigned to another agent.", complaint.id,
        )
    db.commit()
    return complaint


def history(db: Session, complaint_id: int) -> list[ComplaintAssignment]:
    _load_complaint(db, complaint_id)
    return assignment_repository.history(db, complaint_id)
