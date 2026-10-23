from fastapi import APIRouter, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.complaint_comment import CommentCreate, CommentOut
from app.services import comment_service

router = APIRouter(prefix="/complaints", tags=["Comments & Notes"])


@router.post("/{complaint_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED,
             summary="Add a customer-visible comment, or an internal note (staff, is_internal=true)")
def add_comment(complaint_id: int, payload: CommentCreate, db: DbSession, user: CurrentUser):
    return comment_service.add_comment(db, user, complaint_id, payload)


@router.get("/{complaint_id}/comments", response_model=list[CommentOut], summary="List comments (customers never see internal notes)")
def list_comments(complaint_id: int, db: DbSession, user: CurrentUser):
    return comment_service.list_comments(db, user, complaint_id)
