from sqlalchemy.orm import Session

from app.core.constants import ComplaintStatus, NotificationType, Role
from app.core.exceptions import ForbiddenError
from app.core.permissions import ensure_can_access_complaint, is_staff
from app.models import ComplaintComment, SupportAgent, User
from app.repositories import comment_repository, user_repository
from app.schemas.complaint_comment import CommentCreate
from app.services import complaint_service, notification_service, workflow_service


def add_comment(db: Session, user: User, complaint_id: int, payload: CommentCreate) -> ComplaintComment:
    complaint = complaint_service.get_complaint(db, user, complaint_id)  # includes access check
    if payload.is_internal and not is_staff(user):
        raise ForbiddenError("Customers cannot create internal notes")

    comment = ComplaintComment(complaint_id=complaint.id, author_id=user.id, body=payload.body, is_internal=payload.is_internal)
    db.add(comment)

    if not payload.is_internal:
        if user.role == Role.CUSTOMER:
            # notify the assigned agent (or managers when nobody is assigned yet)
            recipients: set[int | None] = set()
            if complaint.assigned_agent_id:
                agent = db.get(SupportAgent, complaint.assigned_agent_id)
                recipients.add(agent.user_id if agent else None)
            else:
                recipients.update(user_repository.active_user_ids_by_roles(db, (Role.SUPPORT_MANAGER,)))
            notification_service.notify(
                db, recipients, NotificationType.NEW_COMMENT, "New customer comment",
                f"Customer commented on complaint {complaint.reference_no}.", complaint.id,
            )
            # a customer reply ends the "waiting for customer" state
            if complaint.status == ComplaintStatus.WAITING_FOR_CUSTOMER:
                workflow_service.change_status(db, complaint, ComplaintStatus.IN_PROGRESS, user, "Customer replied")
        else:
            customer_user = workflow_service.stakeholder_user_ids(db, complaint) - {user.id}
            customer_ids = {uid for uid in customer_user if uid is not None and _is_customer(db, uid)}
            notification_service.notify(
                db, customer_ids, NotificationType.NEW_COMMENT, "New comment on your complaint",
                f"Support replied on complaint {complaint.reference_no}.", complaint.id,
            )
    db.commit()
    return comment


def _is_customer(db: Session, user_id: int) -> bool:
    u = db.get(User, user_id)
    return bool(u and u.role == Role.CUSTOMER)


def list_comments(db: Session, user: User, complaint_id: int) -> list[ComplaintComment]:
    complaint = complaint_service.get_complaint(db, user, complaint_id)
    return comment_repository.list_for_complaint(db, complaint.id, include_internal=is_staff(user))
