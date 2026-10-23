from typing import Annotated, Iterator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import MANAGER_ROLES, STAFF_ROLES, Role
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.jwt import decode_token
from app.db.session import SessionLocal
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    payload = decode_token(token, expected_type="access")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
ManagerUser = Annotated[User, Depends(require_roles(*MANAGER_ROLES))]
StaffUser = Annotated[User, Depends(require_roles(*STAFF_ROLES))]
