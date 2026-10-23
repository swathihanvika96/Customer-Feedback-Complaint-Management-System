from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import ComplaintStatus, Priority
from app.dependencies import CurrentUser, DbSession
from app.models import Complaint
from app.repositories.complaint_repository import SORT_COLUMNS, ComplaintFilters
from app.schemas.common import Page
from app.schemas.complaint import ComplaintCreate, ComplaintOut, ComplaintUpdate, StatusChangeRequest
from app.services import complaint_service
from app.utils.datetime_utils import day_bounds
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED, summary="Create a complaint")
def create_complaint(payload: ComplaintCreate, db: DbSession, user: CurrentUser):
    return complaint_service.create_complaint(db, user, payload)


@router.get(
    "", response_model=Page[ComplaintOut],
    summary="Search complaints with combined filters",
    description="Customers see their own complaints, agents their assigned ones, managers/admins everything. "
                "sort_by: created_at, updated_at, due_at, resolved_at, status, priority, reference_no.",
)
def list_complaints(
    db: DbSession, user: CurrentUser, params: PageParams = Depends(),
    status_: ComplaintStatus | None = Query(None, alias="status"), priority: Priority | None = None,
    category_id: int | None = None, agent_id: int | None = None, customer_id: int | None = None,
    created_from: date | None = None, created_to: date | None = None,
    resolved_from: date | None = None, resolved_to: date | None = None,
    overdue: bool | None = None, q: str | None = Query(None, description="Search reference, title, description"),
):
    c_start, c_end = day_bounds(created_from, created_to)
    r_start, r_end = day_bounds(resolved_from, resolved_to)
    filters = ComplaintFilters(
        status=status_, priority=priority, category_id=category_id, agent_id=agent_id, customer_id=customer_id,
        created_start=c_start, created_end=c_end, resolved_start=r_start, resolved_end=r_end, q=q, overdue=overdue,
    )
    stmt = complaint_service.search_stmt(db, user, filters)
    stmt = apply_sorting(stmt, SORT_COLUMNS, params.sort_by, params.sort_order, "created_at", Complaint.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: DbSession, user: CurrentUser):
    return complaint_service.get_complaint(db, user, complaint_id)


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(complaint_id: int, payload: ComplaintUpdate, db: DbSession, user: CurrentUser):
    return complaint_service.update_complaint(db, user, complaint_id, payload)


@router.post("/{complaint_id}/status", response_model=ComplaintOut,
             summary="Move to in_progress / waiting_for_customer (use dedicated endpoints for assign/resolve/close/reopen)")
def change_status(complaint_id: int, payload: StatusChangeRequest, db: DbSession, user: CurrentUser):
    return complaint_service.change_status(db, user, complaint_id, payload)
