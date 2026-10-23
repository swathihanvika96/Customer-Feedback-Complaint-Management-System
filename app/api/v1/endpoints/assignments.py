from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession, ManagerUser
from app.schemas.complaint import ComplaintOut
from app.schemas.complaint_assignment import AssignmentOut, AssignRequest
from app.services import assignment_service, complaint_service

router = APIRouter(prefix="/complaints", tags=["Assignments"])


@router.post("/{complaint_id}/assign", response_model=ComplaintOut, summary="Assign an open complaint (manager/admin)")
def assign(complaint_id: int, payload: AssignRequest, db: DbSession, manager: ManagerUser):
    return assignment_service.assign(db, manager, complaint_id, payload.agent_id, payload.reason)


@router.post("/{complaint_id}/reassign", response_model=ComplaintOut, summary="Reassign to another agent (manager/admin)")
def reassign(complaint_id: int, payload: AssignRequest, db: DbSession, manager: ManagerUser):
    return assignment_service.reassign(db, manager, complaint_id, payload.agent_id, payload.reason)


@router.get("/{complaint_id}/assignments", response_model=list[AssignmentOut], summary="Assignment history")
def assignment_history(complaint_id: int, db: DbSession, user: CurrentUser):
    complaint_service.get_complaint(db, user, complaint_id)  # access check
    return assignment_service.history(db, complaint_id)
