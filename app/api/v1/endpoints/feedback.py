from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import FeedbackStatus
from app.dependencies import CurrentUser, DbSession, StaffUser
from app.models import Feedback
from app.repositories import audit_repository, feedback_repository
from app.schemas.audit_log import AuditLogOut
from app.schemas.common import Page
from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackStatusUpdate, FeedbackUpdate
from app.services import feedback_service
from app.utils.datetime_utils import day_bounds
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED, summary="Submit feedback (rating 1-5)")
def submit_feedback(payload: FeedbackCreate, db: DbSession, user: CurrentUser):
    return feedback_service.submit_feedback(db, user, payload)


@router.get("", response_model=Page[FeedbackOut],
            summary="Feedback history. Customers see only their own (sort_by: feedback_date, rating)")
def list_feedback(
    db: DbSession, user: CurrentUser, params: PageParams = Depends(),
    customer_id: int | None = None, category_id: int | None = None, status_: FeedbackStatus | None = Query(None, alias="status"),
    rating_min: int | None = Query(None, ge=1, le=5), rating_max: int | None = Query(None, ge=1, le=5),
    date_from: date | None = None, date_to: date | None = None, q: str | None = None,
):
    scope = feedback_service.customer_scope(db, user)
    start, end = day_bounds(date_from, date_to)
    stmt = feedback_repository.search_stmt(
        customer_id=scope if scope is not None else customer_id, category_id=category_id, status=status_,
        rating_min=rating_min, rating_max=rating_max, start=start, end=end, q=q,
    )
    stmt = apply_sorting(stmt, {"feedback_date": Feedback.feedback_date, "rating": Feedback.rating},
                         params.sort_by, params.sort_order, "feedback_date", Feedback.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: int, db: DbSession, user: CurrentUser):
    return feedback_service.get_feedback(db, user, feedback_id)


@router.patch("/{feedback_id}", response_model=FeedbackOut, summary="Edit your own feedback")
def update_feedback(feedback_id: int, payload: FeedbackUpdate, db: DbSession, user: CurrentUser):
    return feedback_service.update_feedback(db, user, feedback_id, payload)


@router.patch("/{feedback_id}/status", response_model=FeedbackOut, summary="Change feedback status (staff)")
def update_feedback_status(feedback_id: int, payload: FeedbackStatusUpdate, db: DbSession, staff: StaffUser):
    return feedback_service.update_status(db, staff, feedback_id, payload.status)


@router.get("/{feedback_id}/history", response_model=list[AuditLogOut], summary="Change history of one feedback entry")
def feedback_history(feedback_id: int, db: DbSession, user: CurrentUser):
    feedback = feedback_service.get_feedback(db, user, feedback_id)
    stmt = audit_repository.search_stmt(entity_type="feedback", entity_id=feedback.id)
    from app.models import AuditLog

    return list(db.scalars(stmt.order_by(AuditLog.created_at, AuditLog.id)).all())
