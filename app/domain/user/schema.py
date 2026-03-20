from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.enums.enums import UserRole
from app.common.schema import CamelModel


class UserCreateSchema(CamelModel):
    """
    Schema for creating a new user.
    """
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    external_id: str | None = None
    university_id: int | None = None
    lab_id: int | None = None
    bio: str | None = None
    organization: str | None = None


class UserCredsSchema(CamelModel):

    id: int
    email: EmailStr | str
    password_hash: str


class UserOutSchema(CamelModel):
    """
    Full user output schema.
    """
    id: int
    name: str
    email: EmailStr | str
    role: UserRole
    external_id: str | None = None
    university_id: int | None = None
    lab_id: int | None = None
    bio: str | None = None
    organization: str | None = None
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
