from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.common.schema import CamelModel
from app.enums.enums import InvestorType, TokenType, UserRole


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserBaseSchema(CamelModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.USER
    external_id: str | None = None


class UserSignupSchema(UserBaseSchema):
    """Public schema for signup requests. Accepts optional role-specific profile."""
    password: str
    investor_profile: "InvestorProfileSchema | None" = None
    researcher_profile: "ResearcherProfileSchema | None" = None
    sponsor_profile: "SponsorProfileSchema | None" = None


class UserCreateDBSchema(UserBaseSchema):
    """Internal schema used to persist users."""
    password_hash: str
    verified: bool = False
    token_hash: str | None = None
    token_type: TokenType | None = None


class UserCredsSchema(CamelModel):
    id: int
    email: EmailStr | str
    password_hash: str
    verified: bool


class UserOutSchema(UserBaseSchema):
    """User output schema without profile data."""
    id: int
    verified: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.isoformat()


class UserWithProfileOutSchema(UserOutSchema):
    """User output including role-specific profile and categories."""
    investor_profile: "InvestorProfileOutSchema | None" = None
    researcher_profile: "ResearcherProfileOutSchema | None" = None
    sponsor_profile: "SponsorProfileOutSchema | None" = None
    categories: list["CategoryRefSchema"] = []


# ---------------------------------------------------------------------------
# Profile schemas
# ---------------------------------------------------------------------------

class InvestorProfileSchema(CamelModel):
    investor_type: InvestorType
    balance: float | None = None


class InvestorProfileOutSchema(InvestorProfileSchema):
    user_id: int
    created_at: datetime
    updated_at: datetime


class ResearcherProfileSchema(CamelModel):
    lab_id: int | None = None
    bio: str | None = None


class ResearcherProfileOutSchema(ResearcherProfileSchema):
    user_id: int
    created_at: datetime
    updated_at: datetime


class SponsorProfileSchema(CamelModel):
    bio: str | None = None
    amount: float | None = None


class SponsorProfileOutSchema(SponsorProfileSchema):
    user_id: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Category reference (for user_category join)
# ---------------------------------------------------------------------------

class CategoryRefSchema(CamelModel):
    category_id: int


class UserCategorySetSchema(CamelModel):
    category_ids: list[int]


# ---------------------------------------------------------------------------
# Auth / utility schemas
# ---------------------------------------------------------------------------

class TokenData(BaseModel):
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
