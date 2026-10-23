from datetime import datetime, timedelta

from app.core.constants import ComplaintStatus, Priority
from app.models import Complaint
from app.services import sla_service

NOW = datetime(2026, 10, 21, 12, 0, 0)


def make(created_offset_h: float, due_hours: float, resolved_offset_h: float | None = None) -> Complaint:
    created = NOW + timedelta(hours=created_offset_h)
    return Complaint(
        id=1, reference_no="CMP-X", priority=Priority.HIGH, status=ComplaintStatus.OPEN,
        created_at=created, due_at=created + timedelta(hours=due_hours),
        resolved_at=None if resolved_offset_h is None else NOW + timedelta(hours=resolved_offset_h),
    )


def test_default_hours_and_due_date(db):
    assert sla_service.hours_for_priority(db, Priority.HIGH) == 4
    assert sla_service.hours_for_priority(db, Priority.MEDIUM) == 12
    assert sla_service.hours_for_priority(db, Priority.LOW) == 24
    assert sla_service.compute_due_at(NOW, 4) == NOW + timedelta(hours=4)


def test_time_remaining_on_track():
    s = sla_service.evaluate(make(-1, 4), now=NOW, warning_minutes=60)
    assert s.state == "on_track" and not s.is_breached
    assert s.time_remaining_seconds == 3 * 3600


def test_at_risk_inside_warning_window():
    s = sla_service.evaluate(make(-3.5, 4), now=NOW, warning_minutes=60)
    assert s.state == "at_risk"
    assert s.time_remaining_seconds == 30 * 60


def test_overdue_active_complaint_is_breached():
    s = sla_service.evaluate(make(-5, 4), now=NOW)
    assert s.is_breached and s.state == "breached"
    assert s.overdue_seconds == 3600 and s.time_remaining_seconds == 0


def test_resolved_within_sla_is_met():
    s = sla_service.evaluate(make(-3, 4, resolved_offset_h=-1), now=NOW)
    assert s.state == "met" and not s.is_breached and s.is_finished
    assert s.resolution_duration_seconds == 2 * 3600
    assert s.time_remaining_seconds is None


def test_resolved_late_is_breached():
    s = sla_service.evaluate(make(-6, 4, resolved_offset_h=-1), now=NOW)
    assert s.state == "breached" and s.is_breached
    assert s.resolution_duration_seconds == 5 * 3600
    assert s.overdue_seconds == 3600
