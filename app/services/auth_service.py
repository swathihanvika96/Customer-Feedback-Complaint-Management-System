from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import AuditAction, Role
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security import hash_password, hash_token, verify_password
from app.models import Customer, RefreshToken, User
from app.repositories import customer_repository, user_repository
from app.schemas.auth import RegisterRequest, TokenPair
from app.services import audit_service
from app.utils.datetime_utils import to_naive_utc, utcnow


def register_customer(db: Session, payload: RegisterRequest) -> User:
    if user_repository.get_by_email(db, payload.email):
        raise ConflictError("Email is already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=Role.CUSTOMER,
    )
    db.add(user)
    db.flush()

    existing = customer_repository.get_by_email(db, payload.email)
    if existing is not None:
        if existing.user_id is not None:
            raise ConflictError("A customer profile with this email already has an account")
        existing.user_id = user.id  # staff pre-created the profile; link it
    else:
        db.add(Customer(user_id=user.id, name=payload.full_name, email=payload.email, phone=payload.phone))
    audit_service.log(db, user.id, AuditAction.USER_REGISTERED, "user", user.id, {"role": Role.CUSTOMER.value})
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = user_repository.get_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, user.role.value)
    refresh, expires = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=to_naive_utc(expires)))
    db.commit()
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _find_valid_refresh(db: Session, token: str) -> RefreshToken:
    decode_token(token, expected_type="refresh")
    from sqlalchemy import select

    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if row is None or row.revoked or row.expires_at < utcnow():
        raise UnauthorizedError("Refresh token is invalid or has been revoked")
    return row


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    row = _find_valid_refresh(db, refresh_token)
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User is inactive")
    row.revoked = True  # rotation: each refresh token is single-use
    return issue_tokens(db, user)


def logout(db: Session, refresh_token: str) -> None:
    try:
        row = _find_valid_refresh(db, refresh_token)
    except UnauthorizedError:
        return  # already invalid: logout is idempotent
    row.revoked = True
    db.commit()


def revoke_all_tokens(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
