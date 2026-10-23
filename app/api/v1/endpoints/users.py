from fastapi import APIRouter, Depends, Query, status

from app.core.constants import Role
from app.dependencies import AdminUser, DbSession
from app.models import User
from app.repositories import user_repository
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut
from app.services import user_service
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/users", tags=["Users (admin)"])


@router.get("", response_model=Page[UserOut], summary="List users (sort_by: created_at, email, full_name, role)")
def list_users(
    db: DbSession, admin: AdminUser, params: PageParams = Depends(),
    role: Role | None = None, is_active: bool | None = None, q: str | None = Query(None, description="Search email / name"),
):
    stmt = user_repository.list_stmt(role, is_active, q)
    stmt = apply_sorting(stmt, {"created_at": User.created_at, "email": User.email, "full_name": User.full_name,
                                "role": User.role}, params.sort_by, params.sort_order, "created_at", User.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create a user with any role")
def create_user(payload: UserCreate, db: DbSession, admin: AdminUser):
    return user_service.create_user(db, admin, payload)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession, admin: AdminUser):
    return user_service.get_user(db, user_id)


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(user_id: int, db: DbSession, admin: AdminUser):
    return user_service.set_active(db, admin, user_id, True)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: DbSession, admin: AdminUser):
    return user_service.set_active(db, admin, user_id, False)
