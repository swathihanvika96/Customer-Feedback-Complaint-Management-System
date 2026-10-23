from pydantic import ConfigDict, BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime
from app.utils.validators import validate_password_strength


class CustomerCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Ravi Kumar",
        "email": "ravi@example.com",
        "phone": "9876543210",
        "company": "ABC Technologies",
        "address": "Bengaluru, Karnataka",
        "password": "Ravi@12345"
    }})

    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=255)
    password: str | None = None  # optional: also create a login account

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str | None) -> str | None:
        return validate_password_strength(v) if v is not None else v


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Ravi Kumar",
        "phone": "9123456780",
        "company": "ABC Technologies Pvt Ltd",
        "address": "Whitefield, Bengaluru, Karnataka"
    }})

    name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=255)


class CustomerOut(ORMModel):
    id: int
    user_id: int | None
    name: str
    email: str
    phone: str | None
    company: str | None
    address: str | None
    is_active: bool
    created_at: UTCDateTime
