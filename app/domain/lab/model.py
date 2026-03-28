from __future__ import annotations

from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin


class LabCategory(Base, TimestampMixin):
    __tablename__ = "lab_category"
    __table_args__ = (PrimaryKeyConstraint("lab_id", "category_id"),)

    lab_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )


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
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
