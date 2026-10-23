from app.core.constants import ComplaintStatus
from app.schemas.common import ORMModel, UTCDateTime


class StatusHistoryOut(ORMModel):
    id: int
    complaint_id: int
    from_status: ComplaintStatus | None
    to_status: ComplaintStatus
    changed_by: int | None
    note: str | None
    created_at: UTCDateTime
