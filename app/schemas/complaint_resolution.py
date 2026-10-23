from pydantic import ConfigDict, BaseModel, Field

from app.schemas.common import ORMModel, UTCDateTime


class ResolveRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "summary": "A replacement laptop was shipped and delivered.",
        "root_cause": "Damaged in transit due to poor packaging",
        "action_taken": "Replacement dispatched; courier claim filed"
    }})

    summary: str = Field(min_length=5, max_length=5000)
    root_cause: str | None = Field(default=None, max_length=5000)
    action_taken: str | None = Field(default=None, max_length=5000)


class CloseRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "note": "Customer confirmed the replacement works"
    }})

    note: str | None = Field(default=None, max_length=500)


class ReopenRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "reason": "The replacement also has a defect"
    }})

    reason: str = Field(min_length=3, max_length=500)


class ResolutionOut(ORMModel):
    id: int
    complaint_id: int
    resolved_by: int
    summary: str
    root_cause: str | None
    action_taken: str | None
    created_at: UTCDateTime
