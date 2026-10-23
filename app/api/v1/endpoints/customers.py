from fastapi import APIRouter, Depends, Query, status

from app.dependencies import CurrentUser, DbSession, ManagerUser, StaffUser
from app.models import Customer
from app.repositories import customer_repository
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import customer_service
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED, summary="Create a customer (staff)")
def create_customer(payload: CustomerCreate, db: DbSession, staff: StaffUser):
    return customer_service.create_customer(db, staff, payload)


@router.get("", response_model=Page[CustomerOut],
            summary="Search / filter customers (sort_by: created_at, name, email, company)")
def list_customers(
    db: DbSession, staff: StaffUser, params: PageParams = Depends(),
    q: str | None = Query(None, description="Search name, email, phone, company"),
    is_active: bool | None = None, company: str | None = None,
):
    stmt = customer_repository.search_stmt(q, is_active, company)
    stmt = apply_sorting(stmt, {"created_at": Customer.created_at, "name": Customer.name, "email": Customer.email,
                                "company": Customer.company}, params.sort_by, params.sort_order, "created_at", Customer.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.get("/me", response_model=CustomerOut, summary="My customer profile")
def my_profile(db: DbSession, user: CurrentUser):
    return customer_service.get_own_profile(db, user)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: DbSession, user: CurrentUser):
    return customer_service.get_customer(db, user, customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: DbSession, user: CurrentUser):
    return customer_service.update_customer(db, user, customer_id, payload)


@router.post("/{customer_id}/activate", response_model=CustomerOut)
def activate_customer(customer_id: int, db: DbSession, manager: ManagerUser):
    return customer_service.set_active(db, manager, customer_id, True)


@router.post("/{customer_id}/deactivate", response_model=CustomerOut)
def deactivate_customer(customer_id: int, db: DbSession, manager: ManagerUser):
    return customer_service.set_active(db, manager, customer_id, False)
