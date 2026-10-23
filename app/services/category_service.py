from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Category
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_category(db: Session, category_id: int) -> Category:
    category = category_repository.get(db, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    return category


def get_active_category(db: Session, category_id: int) -> Category:
    category = category_repository.get(db, category_id)
    if category is None:
        raise BadRequestError(f"Category {category_id} does not exist")
    if not category.is_active:
        raise BadRequestError(f"Category '{category.name}' is deactivated")
    return category


def create_category(db: Session, payload: CategoryCreate) -> Category:
    if category_repository.get_by_name(db, payload.name):
        raise ConflictError("A category with this name already exists")
    category = Category(name=payload.name.strip(), description=payload.description)
    db.add(category)
    db.commit()
    return category


def update_category(db: Session, category_id: int, payload: CategoryUpdate) -> Category:
    category = get_category(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"]:
        other = category_repository.get_by_name(db, changes["name"])
        if other and other.id != category.id:
            raise ConflictError("A category with this name already exists")
        changes["name"] = changes["name"].strip()
    for key, value in changes.items():
        setattr(category, key, value)
    db.commit()
    return category


def set_active(db: Session, category_id: int, active: bool) -> Category:
    category = get_category(db, category_id)
    category.is_active = active
    db.commit()
    return category
