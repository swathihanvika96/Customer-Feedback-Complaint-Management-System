from typing import Any

from app.schemas.common import ORMModel, UTCDateTime


class AuditLogOut(ORMModel):
    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int
    details: dict[str, Any] | None
    created_at: UTCDateTime
