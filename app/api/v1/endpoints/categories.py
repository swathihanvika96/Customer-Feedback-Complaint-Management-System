from fastapi import APIRouter, Depends, Query, status

from app.dependencies import CurrentUser, DbSession, ManagerUser
from app.models import Category
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.services import category_service
from app.utils.pagination import PageParams, make_page, paginate
from app.utils.sorting import apply_sorting

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, manager: ManagerUser):
    return category_service.create_category(db, payload)


@router.get("", response_model=Page[CategoryOut], summary="List categories (sort_by: name, created_at)")
def list_categories(
    db: DbSession, user: CurrentUser, params: PageParams = Depends(),
    is_active: bool | None = None, q: str | None = Query(None),
):
    stmt = category_repository.search_stmt(q, is_active)
    stmt = apply_sorting(stmt, {"name": Category.name, "created_at": Category.created_at},
                         params.sort_by, params.sort_order, "name", Category.id)
    items, total = paginate(db, stmt, params)
    return make_page(items, total, params)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: DbSession, user: CurrentUser):
    return category_service.get_category(db, category_id)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, db: DbSession, manager: ManagerUser):
    return category_service.update_category(db, category_id, payload)


@router.post("/{category_id}/activate", response_model=CategoryOut)
def activate_category(category_id: int, db: DbSession, manager: ManagerUser):
    return category_service.set_active(db, category_id, True)


@router.post("/{category_id}/deactivate", response_model=CategoryOut)
def deactivate_category(category_id: int, db: DbSession, manager: ManagerUser):
    return category_service.set_active(db, category_id, False)
