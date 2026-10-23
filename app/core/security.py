import hashlib

import bcrypt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """Refresh tokens are stored hashed so a DB leak does not leak usable tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
