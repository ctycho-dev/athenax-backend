from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.audit_mixin import TimestampMixin
from app.database.connection import Base
from app.enums.enums import PaperSourceType, PaperStatus, PaperVerificationStatus


class PaperCategory(Base, TimestampMixin):
    __tablename__ = "paper_category"
    __table_args__ = (PrimaryKeyConstraint("paper_id", "category_id"),)

    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )


class PaperVote(Base, TimestampMixin):
    __tablename__ = "paper_votes"
    __table_args__ = (PrimaryKeyConstraint("paper_id", "user_id"),)

    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PaperStatus] = mapped_column(
        SQLEnum(PaperStatus, name="paper_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_type: Mapped[PaperSourceType] = mapped_column(
        SQLEnum(PaperSourceType, name="paper_source_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[PaperVerificationStatus] = mapped_column(
        SQLEnum(PaperVerificationStatus, name="paper_verification_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default="pending",
    )
