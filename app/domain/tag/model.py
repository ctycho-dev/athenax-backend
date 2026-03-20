from __future__ import annotations

from sqlalchemy import String, Integer, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin

if TYPE_CHECKING:
    from app.domain.lab.model import Lab


lab_tags = Table(
    "lab_tags",
    Base.metadata,
    Column("lab_id", ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    labs: Mapped[list["Lab"]] = relationship(
        "Lab",
        secondary=lab_tags,
        back_populates="tags",
        lazy="selectin",
    )
