from __future__ import annotations

from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin


lab_category = Table(
    "lab_category",
    Base.metadata,
    Column("lab_id", ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
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
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary=lab_category,
        back_populates="labs",
        lazy="selectin",
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def category_ids(self) -> list[int]:
        return [category.id for category in self.categories]


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    labs: Mapped[list["Lab"]] = relationship(
        "Lab",
        secondary=lab_category,
        back_populates="categories",
        lazy="selectin",
    )
