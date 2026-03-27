from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.audit_mixin import TimestampMixin
from app.database.connection import Base
from app.enums.enums import InvestorType, TokenType, UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_type: Mapped[TokenType | None] = mapped_column(
        SQLEnum(TokenType, name="token_type"), nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"), default=UserRole.USER, nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class InvestorProfile(Base, TimestampMixin):
    __tablename__ = "investor_profiles"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    investor_type: Mapped[InvestorType] = mapped_column(
        SQLEnum(InvestorType, name="investor_type"), nullable=False
    )
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)


class ResearcherProfile(Base, TimestampMixin):
    __tablename__ = "researcher_profiles"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lab_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("labs.id"), nullable=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)


class SponsorProfile(Base, TimestampMixin):
    __tablename__ = "sponsor_profiles"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)


class UserCategory(Base):
    __tablename__ = "user_category"
    __table_args__ = (PrimaryKeyConstraint("user_id", "category_id"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
