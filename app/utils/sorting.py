from typing import Any

from sqlalchemy import Select

from app.core.exceptions import BadRequestError


def apply_sorting(
    stmt: Select,
    columns: dict[str, Any],
    sort_by: str | None,
    sort_order: str,
    default: str,
    tiebreak: Any = None,
) -> Select:
    key = sort_by or default
    if key not in columns:
        raise BadRequestError(f"Invalid sort_by '{key}'. Allowed values: {', '.join(sorted(columns))}")
    col = columns[key]
    stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
    if tiebreak is not None:
        stmt = stmt.order_by(tiebreak.desc() if sort_order == "desc" else tiebreak.asc())
    return stmt
