from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import Priority
from app.db.base import Base, enum_column
from app.utils.datetime_utils import utcnow


class SLARule(Base):
    __tablename__ = "sla_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    priority: Mapped[Priority] = mapped_column(enum_column(Priority), unique=True)
    resolution_hours: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
