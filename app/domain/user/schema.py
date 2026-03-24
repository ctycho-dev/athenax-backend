from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.enums.enums import UserRole
from app.common.schema import CamelModel


class UserBaseSchema(CamelModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.USER
    external_id: str | None = None
    lab_id: int | None = None
    bio: str | None = None
    organization: str | None = None


class UserSignupSchema(UserBaseSchema):
    """Public schema for signup and user creation requests."""
    password: str


class UserCreateDBSchema(UserBaseSchema):
    """Internal schema used to persist users."""
    password_hash: str
    verified: bool = False
    verification_hash: str | None = None
    reset_hash: str | None = None


class UserCredsSchema(CamelModel):
    id: int
    email: EmailStr | str
    password_hash: str
    verified: bool


class UserOutSchema(UserBaseSchema):
    """Full user output schema."""
    id: int
    verified: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.isoformat()


class TokenData(BaseModel):
    """
    Schema for returning user details.

    Attributes:
        id (int): The user's unique identifier.
    """

    id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Login response."""

    access_token: str
    token_type: str


class MessageSchema(CamelModel):
    message: str


class EmailTokenSchema(CamelModel):
    token: str


class EmailRequestSchema(CamelModel):
    email: EmailStr


class PasswordResetSchema(CamelModel):
    token: str
    password: str
