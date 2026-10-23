"""Timezone strategy
-------------------
* Every timestamp is stored as *naive UTC* (portable across MySQL / PostgreSQL / SQLite).
* ``utcnow()`` is the only way application code obtains "now".
* Timezone-aware input is converted to UTC with ``to_naive_utc``.
* API responses serialise datetimes as ISO-8601 with an explicit ``+00:00`` offset
  (see ``schemas.common.UTCDateTime``), so clients always know they are UTC.
* Date-range filters take calendar dates interpreted in UTC: ``date_from`` is inclusive
  (00:00:00), ``date_to`` is inclusive of the whole day (converted to an exclusive next-day bound).
"""
from datetime import date, datetime, time, timedelta, timezone

from app.core.exceptions import BadRequestError


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def day_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Return (inclusive start, exclusive end) datetimes for an inclusive date range."""
    if date_from and date_to and date_from > date_to:
        raise BadRequestError("date_from must not be after date_to")
    start = datetime.combine(date_from, time.min) if date_from else None
    end = datetime.combine(date_to + timedelta(days=1), time.min) if date_to else None
    return start, end


def seconds_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds())
