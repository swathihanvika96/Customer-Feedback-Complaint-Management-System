import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def enum_column(enum_cls: type[enum.Enum]) -> SAEnum:
    """Store enum *values* in a plain VARCHAR (no native ENUM => portable migrations)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=40,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
