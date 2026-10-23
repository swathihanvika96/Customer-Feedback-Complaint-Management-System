from fastapi import APIRouter, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.complaint import ComplaintOut
from app.schemas.complaint_resolution import CloseRequest, ReopenRequest, ResolutionOut, ResolveRequest
from app.schemas.complaint_status_history import StatusHistoryOut
from app.services import resolution_service

router = APIRouter(prefix="/complaints", tags=["Resolution Workflow"])


@router.post("/{complaint_id}/resolve", response_model=ResolutionOut, status_code=status.HTTP_201_CREATED,
             summary="Resolve a complaint (assigned agent or manager)")
def resolve(complaint_id: int, payload: ResolveRequest, db: DbSession, user: CurrentUser):
    return resolution_service.resolve(db, user, complaint_id, payload)


@router.post("/{complaint_id}/close", response_model=ComplaintOut, summary="Close a resolved complaint")
def close(complaint_id: int, payload: CloseRequest, db: DbSession, user: CurrentUser):
    return resolution_service.close(db, user, complaint_id, payload.note)


@router.post("/{complaint_id}/reopen", response_model=ComplaintOut, summary="Reopen a resolved / recently closed complaint")
def reopen(complaint_id: int, payload: ReopenRequest, db: DbSession, user: CurrentUser):
    return resolution_service.reopen(db, user, complaint_id, payload.reason)


@router.get("/{complaint_id}/resolution", response_model=ResolutionOut, summary="Latest resolution details")
def get_resolution(complaint_id: int, db: DbSession, user: CurrentUser):
    return resolution_service.get_resolution(db, user, complaint_id)


@router.get("/{complaint_id}/status-history", response_model=list[StatusHistoryOut])
def status_history(complaint_id: int, db: DbSession, user: CurrentUser):
    return resolution_service.status_history(db, user, complaint_id)
