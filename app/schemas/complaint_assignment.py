from pydantic import ConfigDict, BaseModel, Field

from app.schemas.common import ORMModel, UTCDateTime


class AssignRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "agent_id": 1,
        "reason": "Specialises in hardware delivery issues"
    }})

    agent_id: int
    reason: str | None = Field(default=None, max_length=255)


class AssignmentOut(ORMModel):
    id: int
    complaint_id: int
    agent_id: int
    assigned_by: int
    reason: str | None
    assigned_at: UTCDateTime
    unassigned_at: UTCDateTime | None
    is_active: bool
