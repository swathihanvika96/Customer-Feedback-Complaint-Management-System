from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Customer Feedback & Complaint Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # mysql+pymysql://user:pass@localhost:3306/feedback_db
    # postgresql+psycopg2://user:pass@localhost:5432/feedback_db
    DATABASE_URL: str = "sqlite:///./app.db"
    AUTO_CREATE_TABLES: bool = False  # dev convenience only; use Alembic otherwise

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # Business rules
    SLA_WARNING_MINUTES: int = 60  # "approaching deadline" window
    SLA_CHECK_INTERVAL_SECONDS: int = 0  # 0 = disabled; use POST /sla/check from a cron instead
    REOPEN_WINDOW_DAYS: int = 7  # closed complaints can be reopened within this window

    # Optional bootstrap admin (created on startup if no user with this email exists)
    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None
    FIRST_ADMIN_NAME: str = "System Admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
