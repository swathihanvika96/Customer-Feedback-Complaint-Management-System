from sqlalchemy import or_


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def text_search(columns: list, q: str | None):
    """Case-insensitive 'contains' search across several columns. Returns None when q is empty."""
    if not q or not q.strip():
        return None
    pattern = f"%{escape_like(q.strip())}%"
    return or_(*[col.ilike(pattern, escape="\\") for col in columns])
