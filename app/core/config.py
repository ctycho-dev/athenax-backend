""" Configuration """
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_DIR = '.env'

if os.getenv('mode') == 'dev':
    ENV_DIR = './.env.dev'


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=['.env', ENV_DIR],
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False,
    )

    # FastAPI
    host: str
    port: int
    api_version: str

    # Privy
    PRIVY_JWSK_URL: str
    PRIVY_APP_ID: str
    
    # Mongo
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    MONGO_INITDB_DATABASE: str

    # STORJ
    STORJ_ACCESS_KEY: str
    STORJ_SECRET_KEY: str
    STORJ_ENDPOINT: str

    # Redis
    redis_host: str
    redis_port: int
    mode: str

    # Database
    db_hostname: str
    db_port: int
    db_name: str
    db_username: str
    db_password: str

    # Email
    email_from: str
    email_pwd: str
    email_to: str

    # Creds
    AUTH_PEPPER: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


settings = Settings()
