import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.init_db import seed_defaults
from app.db.session import SessionLocal, engine
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.services import sla_service

logger = logging.getLogger(__name__)


def _run_sla_check() -> None:
    with SessionLocal() as db:
        sla_service.run_check(db)


async def _sla_loop(interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(_run_sla_check)
        except Exception:  # keep the loop alive
            logger.exception("SLA check failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.DEBUG)
    if settings.AUTO_CREATE_TABLES:
        import app.models  # noqa: F401

        Base.metadata.create_all(engine)
    try:
        with SessionLocal() as db:
            seed_defaults(db)
    except Exception:
        logger.exception("Seeding failed (have the migrations been applied? run: alembic upgrade head)")
    task = asyncio.create_task(_sla_loop(settings.SLA_CHECK_INTERVAL_SECONDS)) if settings.SLA_CHECK_INTERVAL_SECONDS > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Collect customer feedback, manage complaints, assign support agents, track SLAs and measure satisfaction.\n\n"
        "**Auth**: register or log in at `/api/v1/auth/login`, then click *Authorize* (username = email). "
        "All timestamps are UTC (ISO-8601)."
    ),
    lifespan=lifespan,
)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
