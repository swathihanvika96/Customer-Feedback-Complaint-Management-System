from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Role
from app.db.base import Base, enum_column
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.support_agent import SupportAgent


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    customer_profile: Mapped[Optional["Customer"]] = relationship(back_populates="user", uselist=False)
    agent_profile: Mapped[Optional["SupportAgent"]] = relationship(back_populates="user", uselist=False)
