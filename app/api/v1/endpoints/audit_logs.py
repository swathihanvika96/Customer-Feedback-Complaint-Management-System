from datetime import date

from fastapi import APIRouter, Depends

from app.dependencies import DbSession, ManagerUser
from app.models import AuditLog
from app.repositories import audit_repository
from app.schemas.audit_log import AuditLogOut
from app.schemas.common import Page
from app.utils.datetime_utils import day_bounds
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=Page[AuditLogOut], summary="Audit trail (manager/admin). sort_by: created_at, action")
def list_audit_logs(
    db: DbSession, manager: ManagerUser, params: PageParams = Depends(),
    actor_id: int | None = None, action: str | None = None, entity_type: str | None = None,
    entity_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
):
    start, end = day_bounds(date_from, date_to)
    stmt = audit_repository.search_stmt(actor_id=actor_id, action=action, entity_type=entity_type,
                                        entity_id=entity_id, start=start, end=end)
    stmt = apply_sorting(stmt, {"created_at": AuditLog.created_at, "action": AuditLog.action},
                         params.sort_by, params.sort_order, "created_at", AuditLog.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)
