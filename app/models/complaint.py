from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ComplaintStatus, Priority, Severity
from app.db.base import Base, enum_column
from app.utils.datetime_utils import utcnow


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_status_priority", "status", "priority"),
        Index("ix_complaints_status_due", "status", "due_at"),
        Index("ix_complaints_customer_created", "customer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[Priority] = mapped_column(enum_column(Priority), index=True)
    severity: Mapped[Severity] = mapped_column(enum_column(Severity))
    status: Mapped[ComplaintStatus] = mapped_column(enum_column(ComplaintStatus), default=ComplaintStatus.OPEN, index=True)
    attachment_urls: Mapped[list] = mapped_column(JSON, default=list)
    assigned_agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("support_agents.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    due_at: Mapped[datetime] = mapped_column(index=True)  # SLA deadline (UTC)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    reopen_count: Mapped[int] = mapped_column(default=0)

    # de-duplication markers for SLA notifications (reset on reopen / priority change)
    sla_warning_sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    sla_breach_notified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
