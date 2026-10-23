import pytest

from app.core.constants import ComplaintStatus as S
from app.core.exceptions import InvalidTransitionError
from app.services.workflow_service import ALLOWED_TRANSITIONS, can_transition, validate_transition


def test_cannot_close_without_resolving():
    for status in (S.OPEN, S.ASSIGNED, S.IN_PROGRESS, S.WAITING_FOR_CUSTOMER, S.REOPENED):
        assert not can_transition(status, S.CLOSED)
        with pytest.raises(InvalidTransitionError):
            validate_transition(status, S.CLOSED)


def test_happy_path():
    path = [S.OPEN, S.ASSIGNED, S.IN_PROGRESS, S.RESOLVED, S.CLOSED]
    for a, b in zip(path, path[1:]):
        validate_transition(a, b)


def test_reopen_paths():
    validate_transition(S.RESOLVED, S.REOPENED)
    validate_transition(S.CLOSED, S.REOPENED)
    validate_transition(S.REOPENED, S.ASSIGNED)


def test_open_cannot_be_resolved_directly():
    with pytest.raises(InvalidTransitionError) as exc:
        validate_transition(S.OPEN, S.RESOLVED)
    assert "assigned" in str(exc.value)


def test_every_status_has_rules():
    assert set(ALLOWED_TRANSITIONS) == set(S)
