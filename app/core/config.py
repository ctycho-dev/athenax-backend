import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file():
    mode = os.getenv('mode', 'prod')
    return '../.env.dev' if mode in ['dev', 'test'] else '.env'
    # return '../.env.dev' if mode in ['dev', 'test'] else '../.env'
    # return f'../.env.{mode}' if mode in ['dev', 'test'] else '.env'


class ApiV1Prefix(BaseModel):
    prefix: str = "/api/v1"
    user: str = "/user"


class ApiV2Prefix(BaseModel):
    prefix: str = "/api/v2"


class ApiPrefix(BaseModel):
    v1: ApiV1Prefix = ApiV1Prefix()
    v2: ApiV2Prefix = ApiV2Prefix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=['.env', get_env_file()],
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False,
    )

    BASE_URL: str
    api: ApiPrefix = ApiPrefix()
    MODE: str = 'prod'
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

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Convert async URL to sync URL for Alembic"""
        # Convert postgresql+asyncpg://... to postgresql://...
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()
