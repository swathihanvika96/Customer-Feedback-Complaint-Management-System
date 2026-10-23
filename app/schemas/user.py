from pydantic import ConfigDict, BaseModel, EmailStr, Field, field_validator

from app.core.constants import Role
from app.schemas.common import ORMModel, UTCDateTime
from app.utils.validators import validate_password_strength


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: UTCDateTime


class UserCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "email": "meena.manager@example.com",
        "full_name": "Meena Iyer",
        "password": "Meena@12345",
        "role": "support_manager",
        "department": None
    }})

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str
    role: Role
    department: str | None = Field(default=None, max_length=100)  # used for support agents

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)
