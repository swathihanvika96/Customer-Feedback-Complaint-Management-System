from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args, echo=settings.DEBUG)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
