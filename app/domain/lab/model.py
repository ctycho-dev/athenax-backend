from __future__ import annotations

from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin
from app.domain.tag.model import lab_tags

if TYPE_CHECKING:
    from app.domain.tag.model import Tag


class Lab(Base, TimestampMixin):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=lab_tags,
        back_populates="labs",
        lazy="selectin",
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
