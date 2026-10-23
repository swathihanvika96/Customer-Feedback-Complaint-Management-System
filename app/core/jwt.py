import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.core.exceptions import UnauthorizedError


def _encode(sub: int, token_type: str, expires_delta: timedelta, extra: dict | None = None) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires = now + expires_delta
    payload = {
        "sub": str(sub),
        "type": token_type,
        "iat": now,
        "exp": expires,
        "jti": uuid.uuid4().hex,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM), expires


def create_access_token(user_id: int, role: str) -> str:
    token, _ = _encode(user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), {"role": role})
    return token


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    return _encode(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")
    return payload
