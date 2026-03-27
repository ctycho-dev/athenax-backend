from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.audit_mixin import TimestampMixin
from app.database.connection import Base


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    labs: Mapped[list["Lab"]] = relationship(  # type: ignore[name-defined]
        "Lab",
        secondary="lab_category",
        back_populates="categories",
        lazy="selectin",
    )
