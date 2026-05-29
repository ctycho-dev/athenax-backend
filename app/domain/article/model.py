from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.audit_mixin import TimestampMixin, UserAuditMixin, SoftDeleteMixin
from app.database.connection import Base
from app.enums.enums import ArticleStatus, ArticleType


class ArticleTag(Base, TimestampMixin):
    __tablename__ = "article_tag"
    __table_args__ = (PrimaryKeyConstraint("article_id", "tag_id"),)

    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )


class Article(Base, TimestampMixin, UserAuditMixin, SoftDeleteMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ArticleStatus] = mapped_column(
        SQLEnum(ArticleStatus, name="article_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=ArticleStatus.DRAFT.value,
    )
    article_type: Mapped[ArticleType] = mapped_column(
        SQLEnum(ArticleType, name="article_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
