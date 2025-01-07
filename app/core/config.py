""" Configuration """
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # FastAPI
    host: str
    port: int
    # Redis
    redis_host: str
    redis_port: int
    mode: str
    # Database
    db_hostname: str
    db_port: str
    db_name: str
    db_username: str
    db_password: str
    # Email
    email_from: str
    email_pwd: str
    email_to: str

    # Creds
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    class Config:
        env_file = '.env'


settings = Settings()
