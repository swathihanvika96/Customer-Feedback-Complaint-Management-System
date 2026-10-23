from sqlalchemy.orm import Session

from app.core.constants import AuditAction, Role
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import Customer, SupportAgent, User
from app.repositories import customer_repository, user_repository
from app.schemas.user import UserCreate
from app.services import audit_service, auth_service


def create_user(db: Session, actor: User, payload: UserCreate) -> User:
    if user_repository.get_by_email(db, payload.email):
        raise ConflictError("Email is already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    if payload.role == Role.CUSTOMER:
        if customer_repository.get_by_email(db, payload.email):
            raise ConflictError("A customer with this email already exists")
        db.add(Customer(user_id=user.id, name=payload.full_name, email=payload.email))
    elif payload.role == Role.SUPPORT_AGENT:
        db.add(SupportAgent(user_id=user.id, department=payload.department))
    audit_service.log(db, actor.id, AuditAction.USER_CREATED, "user", user.id, {"role": payload.role.value, "email": user.email})
    db.commit()
    return user


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get(db, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def set_active(db: Session, actor: User, user_id: int, active: bool) -> User:
    user = get_user(db, user_id)
    if user.id == actor.id and not active:
        raise BadRequestError("You cannot deactivate your own account")
    user.is_active = active
    if user.customer_profile:
        user.customer_profile.is_active = active
    if user.agent_profile:
        user.agent_profile.is_active = active
    if not active:
        auth_service.revoke_all_tokens(db, user.id)
    audit_service.log(
        db, actor.id, AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED, "user", user.id
    )
    db.commit()
    return user
