from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.audit_mixin import TimestampMixin, UserAuditMixin, SoftDeleteMixin
from app.database.connection import Base
from app.enums.enums import BroadcastStatus, BroadcastType


class BroadcastTag(Base, TimestampMixin):
    __tablename__ = "broadcast_tag"
    __table_args__ = (PrimaryKeyConstraint("broadcast_id", "tag_id"),)

    broadcast_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )


class Broadcast(Base, TimestampMixin, UserAuditMixin, SoftDeleteMixin):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    embed_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    broadcast_type: Mapped[BroadcastType] = mapped_column(
        SQLEnum(BroadcastType, name="broadcast_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[BroadcastStatus] = mapped_column(
        SQLEnum(BroadcastStatus, name="broadcast_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=BroadcastStatus.DRAFT.value,
    )
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    origin_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
