from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.enums.enums import UserRole
from app.common.schema import CamelModel


class UserCreateSchema(CamelModel):
    """
    Schema for creating a new user.
    """
    name: str | None = None
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER


class UserCredsSchema(CamelModel):

    id: int
    email: EmailStr | str
    password: str


class UserOutSchema(CamelModel):
    """
    Full user output schema.
    """
    id: int
    name: str | None
    email: EmailStr | str
    role: UserRole
    is_active: bool
    created_at: datetime

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
