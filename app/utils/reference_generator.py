import secrets
from datetime import datetime


def generate_reference(prefix: str = "CMP", now: datetime | None = None) -> str:
    """e.g. CMP-20261021-A3F9C2 (date + 6 random hex chars)."""
    now = now or datetime.utcnow()
    return f"{prefix}-{now:%Y%m%d}-{secrets.token_hex(3).upper()}"
