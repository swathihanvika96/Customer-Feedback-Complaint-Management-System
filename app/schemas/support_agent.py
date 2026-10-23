from pydantic import ConfigDict, BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime
from app.utils.validators import validate_password_strength


class AgentCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "email": "anita.agent@example.com",
        "full_name": "Anita Sharma",
        "password": "Anita@12345",
        "department": "Technical Support",
        "max_workload": 10
    }})

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str
    department: str | None = Field(default=None, max_length=100)
    max_workload: int = Field(default=10, ge=1, le=200)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)


class AgentUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "department": "Billing Support",
        "max_workload": 15
    }})

    department: str | None = Field(default=None, max_length=100)
    max_workload: int | None = Field(default=None, ge=1, le=200)


class AgentOut(ORMModel):
    id: int
    user_id: int
    full_name: str
    email: str
    department: str | None
    max_workload: int
    is_active: bool
    created_at: UTCDateTime


class AgentWorkloadOut(BaseModel):
    agent_id: int
    agent_name: str
    max_workload: int
    active_complaints: int
    available_capacity: int
    by_status: dict[str, int]
