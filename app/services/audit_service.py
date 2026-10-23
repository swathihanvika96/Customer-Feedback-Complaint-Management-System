from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import AuditAction
from app.models import AuditLog


def log(
    db: Session,
    actor_id: int | None,
    action: AuditAction,
    entity_type: str,
    entity_id: int,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Adds the audit row to the caller's transaction (no commit) so it is atomic with the change."""
    entry = AuditLog(actor_id=actor_id, action=action.value, entity_type=entity_type, entity_id=entity_id, details=details or {})
    db.add(entry)
    return entry


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {k: {"from": before.get(k), "to": after[k]} for k in after if before.get(k) != after[k]}
