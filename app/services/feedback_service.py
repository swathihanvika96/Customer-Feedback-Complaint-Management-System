from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.constants import FINISHED_STATUSES, AuditAction, FeedbackStatus, Role
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import is_staff
from app.models import Feedback, User
from app.repositories import complaint_repository, customer_repository, feedback_repository
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate
from app.services import audit_service, category_service, customer_service
from app.utils.datetime_utils import utcnow

DUPLICATE_WINDOW = timedelta(minutes=5)


def validate_rating(rating: int) -> int:
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        raise BadRequestError("Rating must be an integer between 1 and 5")
    return rating


def submit_feedback(db: Session, user: User, payload: FeedbackCreate) -> Feedback:
    validate_rating(payload.rating)
    customer = customer_service.resolve_customer_for_actor(db, user, payload.customer_id)
    category_service.get_active_category(db, payload.category_id)

    if payload.complaint_id is not None:
        complaint = complaint_repository.get(db, payload.complaint_id)
        if complaint is None or complaint.customer_id != customer.id:
            raise BadRequestError("Complaint not found for this customer")
        if complaint.status not in FINISHED_STATUSES:
            raise BadRequestError("Feedback can only be linked to a resolved or closed complaint")
        if feedback_repository.get_for_complaint(db, customer.id, complaint.id):
            raise ConflictError("Feedback has already been submitted for this complaint")

    duplicate = feedback_repository.find_recent_duplicate(
        db, customer.id, payload.category_id, payload.rating, payload.description, utcnow() - DUPLICATE_WINDOW
    )
    if duplicate:
        raise ConflictError("Identical feedback was just submitted")

    feedback = Feedback(
        customer_id=customer.id,
        category_id=payload.category_id,
        complaint_id=payload.complaint_id,
        rating=payload.rating,
        description=payload.description,
    )
    db.add(feedback)
    db.flush()
    audit_service.log(db, user.id, AuditAction.FEEDBACK_CREATED, "feedback", feedback.id,
                      {"rating": feedback.rating, "category_id": feedback.category_id})
    db.commit()
    return feedback


def get_feedback(db: Session, user: User, feedback_id: int) -> Feedback:
    feedback = feedback_repository.get(db, feedback_id)
    if feedback is None:
        raise NotFoundError("Feedback not found")
    if user.role == Role.CUSTOMER:
        customer = customer_repository.get_by_user_id(db, user.id)
        if customer is None or customer.id != feedback.customer_id:
            raise ForbiddenError("You can only access your own feedback")
    return feedback


def customer_scope(db: Session, user: User) -> int | None:
    """For customers returns their customer id (list is restricted to it); staff -> None (no restriction)."""
    if is_staff(user):
        return None
    customer = customer_repository.get_by_user_id(db, user.id)
    if customer is None:
        raise BadRequestError("No customer profile is linked to this account")
    return customer.id


def update_feedback(db: Session, user: User, feedback_id: int, payload: FeedbackUpdate) -> Feedback:
    feedback = get_feedback(db, user, feedback_id)
    if user.role != Role.CUSTOMER:
        raise ForbiddenError("Only the customer who submitted feedback can edit it")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise BadRequestError("No fields to update")
    if "rating" in changes:
        validate_rating(changes["rating"])
    if "category_id" in changes:
        category_service.get_active_category(db, changes["category_id"])
    before = {k: getattr(feedback, k) for k in changes}
    for key, value in changes.items():
        setattr(feedback, key, value)
    audit_service.log(db, user.id, AuditAction.FEEDBACK_UPDATED, "feedback", feedback.id, audit_service.diff(before, changes))
    db.commit()
    return feedback


def update_status(db: Session, user: User, feedback_id: int, status: FeedbackStatus) -> Feedback:
    feedback = get_feedback(db, user, feedback_id)
    before = feedback.status.value
    feedback.status = status
    audit_service.log(db, user.id, AuditAction.FEEDBACK_UPDATED, "feedback", feedback.id,
                      {"status": {"from": before, "to": status.value}})
    db.commit()
    return feedback
