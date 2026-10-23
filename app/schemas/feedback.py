from pydantic import ConfigDict, BaseModel, Field

from app.core.constants import FeedbackStatus
from app.schemas.common import ORMModel, UTCDateTime


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "category_id": 1,
        "rating": 4,
        "description": "Delivery was quick and the product quality is good.",
        "complaint_id": None,
        "customer_id": None
    }})

    category_id: int
    rating: int = Field(ge=1, le=5, description="Rating from 1 (worst) to 5 (best)")
    description: str = Field(min_length=3, max_length=5000)
    complaint_id: int | None = Field(default=None, description="Optional: link to your resolved/closed complaint")
    customer_id: int | None = Field(default=None, description="Staff only: submit on behalf of a customer")


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "rating": 5,
        "description": "Updated: support resolved my issue very quickly."
    }})

    category_id: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, min_length=3, max_length=5000)


class FeedbackStatusUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "reviewed"
    }})

    status: FeedbackStatus


class FeedbackOut(ORMModel):
    id: int
    customer_id: int
    category_id: int
    complaint_id: int | None
    rating: int
    description: str
    status: FeedbackStatus
    feedback_date: UTCDateTime
    updated_at: UTCDateTime
