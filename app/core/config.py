from typing import Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


def _cfg(env_prefix: str = "") -> SettingsConfigDict:
    return SettingsConfigDict(
        env_file=['.env'],
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False,
        env_prefix=env_prefix,
    )


class ApiV1Prefix(BaseModel):
    prefix: str = "/api/v1"
    user: str = "/user"
    university: str = "/university"
    lab: str = "/lab"
    category: str = "/category"
    paper: str = "/paper"
    product: str = "/product"


class ApiPrefix(BaseModel):
    v1: ApiV1Prefix = ApiV1Prefix()


class DbConfig(BaseSettings):
    url: str
    direct_url: str

    model_config = _cfg("DATABASE_")


class RedisConfig(BaseSettings):
    url: str
    use_ipv6: bool = False

    model_config = _cfg("REDIS_")


class AuthConfig(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int
    cookie_secure: bool = True
    cookie_samesite: Literal['lax', 'strict', 'none'] = 'none'

    model_config = _cfg("")


class ResendConfig(BaseSettings):
    api_key: str
    from_address: str = "AthenaX <noreply@athenax.co>"

    model_config = _cfg("RESEND_")


class Settings(BaseSettings):
    model_config = _cfg("")

    cors_origin: str = ''
    frontend_url: str = 'http://localhost:3000'

    api: ApiPrefix = ApiPrefix()
    db: DbConfig = DbConfig()  # pyright: ignore[reportCallIssue]
    redis: RedisConfig = RedisConfig()  # pyright: ignore[reportCallIssue]
    auth: AuthConfig = AuthConfig()  # pyright: ignore[reportCallIssue]
    resend: ResendConfig = ResendConfig()  # pyright: ignore[reportCallIssue]

    @property
    def email_verify_url(self) -> str:
        return f"{self.frontend_url.rstrip('/')}/verify-email"

    @property
    def password_reset_url(self) -> str:
        return f"{self.frontend_url.rstrip('/')}/reset-password"

settings = Settings()  # pyright: ignore[reportCallIssue] - values come from .env
