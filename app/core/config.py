from typing import Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiV1Prefix(BaseModel):
    prefix: str = "/api/v1"
    user: str = "/user"
    university: str = "/university"
    lab: str = "/lab"
    category: str = "/category"
    paper: str = "/paper"
    product: str = "/product"


class ApiV2Prefix(BaseModel):
    prefix: str = "/api/v2"


class ApiPrefix(BaseModel):
    v1: ApiV1Prefix = ApiV1Prefix()
    v2: ApiV2Prefix = ApiV2Prefix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=['.env'],
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False,
    )

    BASE_URL: str
    api: ApiPrefix = ApiPrefix()
    RUN_MODE: str = 'prod'
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal['lax', 'strict', 'none'] = 'none'
    PROXY_URL: str | None = None

    ADMIN_LOGIN: str
    ADMIN_PWD: str

    # Postgres
    DATABASE_URL: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    # Oauth2
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    SMTP_FROM: str
    SMTP_FROM_NAME: str = "AthenaX"
    SMTP_STARTTLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT: float = 10.0

    FRONTEND_URL: str = 'http://localhost:3000'

    @property
    def EMAIL_VERIFY_URL(self) -> str:
        return f"{self.FRONTEND_URL.rstrip('/')}/verify-email"

    @property
    def PASSWORD_RESET_URL(self) -> str:
        return f"{self.FRONTEND_URL.rstrip('/')}/reset-password"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Convert async URL to sync URL for Alembic"""
        # Convert postgresql+asyncpg://... to postgresql://...
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()  # pyright: ignore[reportCallIssue] - values come from .env
