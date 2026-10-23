from sqlalchemy.orm import Session

from app.core.constants import AuditAction, Role
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import is_staff
from app.core.security import hash_password
from app.models import Customer, User
from app.repositories import customer_repository, user_repository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services import audit_service


def create_customer(db: Session, actor: User, payload: CustomerCreate) -> Customer:
    if customer_repository.get_by_email(db, payload.email):
        raise ConflictError("A customer with this email already exists")
    user_id = None
    if payload.password:
        if user_repository.get_by_email(db, payload.email):
            raise ConflictError("A user with this email already exists")
        user = User(
            email=payload.email,
            full_name=payload.name,
            hashed_password=hash_password(payload.password),
            role=Role.CUSTOMER,
        )
        db.add(user)
        db.flush()
        user_id = user.id
    customer = Customer(
        user_id=user_id, name=payload.name, email=payload.email, phone=payload.phone,
        company=payload.company, address=payload.address,
    )
    db.add(customer)
    db.flush()
    audit_service.log(db, actor.id, AuditAction.CUSTOMER_CREATED, "customer", customer.id, {"email": customer.email})
    db.commit()
    return customer


def get_customer(db: Session, user: User, customer_id: int) -> Customer:
    customer = customer_repository.get(db, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    if not is_staff(user) and customer.user_id != user.id:
        raise ForbiddenError("You can only access your own profile")
    return customer


def get_own_profile(db: Session, user: User) -> Customer:
    customer = customer_repository.get_by_user_id(db, user.id)
    if customer is None:
        raise NotFoundError("No customer profile is linked to this account")
    return customer


def update_customer(db: Session, user: User, customer_id: int, payload: CustomerUpdate) -> Customer:
    customer = get_customer(db, user, customer_id)
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(customer, k) for k in changes}
    for key, value in changes.items():
        setattr(customer, key, value)
    audit_service.log(db, user.id, AuditAction.CUSTOMER_UPDATED, "customer", customer.id, audit_service.diff(before, changes))
    db.commit()
    return customer


def set_active(db: Session, actor: User, customer_id: int, active: bool) -> Customer:
    customer = customer_repository.get(db, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    customer.is_active = active
    if customer.user_id:
        linked = db.get(User, customer.user_id)
        if linked:
            linked.is_active = active
    audit_service.log(db, actor.id, AuditAction.CUSTOMER_UPDATED, "customer", customer.id, {"is_active": active})
    db.commit()
    return customer


def resolve_customer_for_actor(db: Session, user: User, customer_id: int | None) -> Customer:
    """Customers act as themselves; staff must name the customer. Customer must be active."""
    if user.role == Role.CUSTOMER:
        customer = customer_repository.get_by_user_id(db, user.id)
        if customer is None:
            raise BadRequestError("No customer profile is linked to this account")
        if customer_id is not None and customer_id != customer.id:
            raise ForbiddenError("You cannot act on behalf of another customer")
    else:
        if customer_id is None:
            raise BadRequestError("customer_id is required when staff act on behalf of a customer")
        customer = customer_repository.get(db, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
    if not customer.is_active:
        raise BadRequestError("Customer account is deactivated")
    return customer
