from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import (
    ACTIVE_STATUSES,
    DEFAULT_SLA_HOURS,
    AuditAction,
    NotificationType,
    Priority,
    Role,
)
from app.models import Complaint, SLARule, SupportAgent, User
from app.repositories import complaint_repository, user_repository
from app.schemas.sla import SLACheckResult, SLAStatusOut
from app.services import audit_service, notification_service
from app.utils.datetime_utils import seconds_between, utcnow


def get_rules(db: Session) -> list[SLARule]:
    return list(db.scalars(select(SLARule).order_by(SLARule.resolution_hours)).all())


def hours_for_priority(db: Session, priority: Priority) -> int:
    rule = db.scalar(select(SLARule).where(SLARule.priority == priority))
    return rule.resolution_hours if rule else DEFAULT_SLA_HOURS[priority]


def compute_due_at(created_at: datetime, hours: int) -> datetime:
    return created_at + timedelta(hours=hours)


def update_rule(db: Session, actor: User, priority: Priority, hours: int) -> SLARule:
    rule = db.scalar(select(SLARule).where(SLARule.priority == priority))
    before = rule.resolution_hours if rule else None
    if rule is None:
        rule = SLARule(priority=priority, resolution_hours=hours)
        db.add(rule)
    else:
        rule.resolution_hours = hours
    db.flush()
    audit_service.log(db, actor.id, AuditAction.SLA_RULE_UPDATED, "sla_rule", rule.id,
                      {"priority": priority.value, "from": before, "to": hours})
    db.commit()
    return rule


def evaluate(complaint: Complaint, now: datetime | None = None, warning_minutes: int | None = None) -> SLAStatusOut:
    """Pure SLA calculation (no DB access). All datetimes are naive UTC.

    * finished (resolved_at set):  breached  <=>  resolved_at > due_at ; duration = resolved_at - created_at
    * active:                      breached  <=>  now > due_at ; remaining = due_at - now
                                   at_risk   <=>  0 < remaining <= warning window
    """
    now = now or utcnow()
    warning = timedelta(minutes=settings.SLA_WARNING_MINUTES if warning_minutes is None else warning_minutes)
    finished = complaint.resolved_at is not None
    remaining = overdue = duration = None

    if finished:
        duration = seconds_between(complaint.created_at, complaint.resolved_at)
        breached = complaint.resolved_at > complaint.due_at
        state = "breached" if breached else "met"
        if breached:
            overdue = seconds_between(complaint.due_at, complaint.resolved_at)
    else:
        delta = seconds_between(now, complaint.due_at)
        if delta < 0:
            breached, state, overdue, remaining = True, "breached", -delta, 0
        else:
            breached, remaining = False, delta
            state = "at_risk" if complaint.due_at - now <= warning else "on_track"

    return SLAStatusOut(
        complaint_id=complaint.id,
        reference_no=complaint.reference_no,
        priority=complaint.priority,
        created_at=complaint.created_at,
        due_at=complaint.due_at,
        sla_hours=round(seconds_between(complaint.created_at, complaint.due_at) / 3600, 2),
        state=state,
        is_breached=breached,
        is_finished=finished,
        time_remaining_seconds=remaining,
        overdue_seconds=overdue,
        resolution_duration_seconds=duration,
    )


def reset_sla_markers(complaint: Complaint) -> None:
    complaint.sla_warning_sent_at = None
    complaint.sla_breach_notified_at = None


def _recipients(db: Session, complaint: Complaint, include_managers: bool) -> set[int | None]:
    ids: set[int | None] = set()
    if complaint.assigned_agent_id:
        agent = db.get(SupportAgent, complaint.assigned_agent_id)
        ids.add(agent.user_id if agent else None)
    if include_managers or not ids:
        ids.update(user_repository.active_user_ids_by_roles(db, (Role.SUPPORT_MANAGER,)))
    return ids


def run_check(db: Session) -> SLACheckResult:
    """Create SLA notifications. Safe to call repeatedly: each complaint is notified once per SLA cycle."""
    now = utcnow()
    window_end = now + timedelta(minutes=settings.SLA_WARNING_MINUTES)

    approaching = db.scalars(
        select(Complaint).where(
            Complaint.status.in_(ACTIVE_STATUSES),
            Complaint.due_at > now,
            Complaint.due_at <= window_end,
            Complaint.sla_warning_sent_at.is_(None),
        )
    ).all()
    for c in approaching:
        notification_service.notify(
            db, _recipients(db, c, include_managers=False), NotificationType.SLA_APPROACHING,
            "SLA deadline approaching", f"Complaint {c.reference_no} is due at {c.due_at:%Y-%m-%d %H:%M} UTC.", c.id,
        )
        c.sla_warning_sent_at = now

    breached = db.scalars(
        select(Complaint).where(
            Complaint.status.in_(ACTIVE_STATUSES),
            Complaint.due_at <= now,
            Complaint.sla_breach_notified_at.is_(None),
        )
    ).all()
    for c in breached:
        notification_service.notify(
            db, _recipients(db, c, include_managers=True), NotificationType.SLA_BREACHED,
            "SLA breached", f"Complaint {c.reference_no} missed its SLA deadline ({c.due_at:%Y-%m-%d %H:%M} UTC).", c.id,
        )
        c.sla_breach_notified_at = now
        if c.sla_warning_sent_at is None:
            c.sla_warning_sent_at = now

    db.commit()
    return SLACheckResult(approaching_notified=len(approaching), breached_notified=len(breached))


def overdue_stmt(now: datetime | None = None, scope_agent_id: int | None = None):
    return complaint_repository.overdue_stmt(now or utcnow(), scope_agent_id)
