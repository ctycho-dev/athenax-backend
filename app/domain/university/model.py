from sqlalchemy import String, Integer, CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin


class University(Base, TimestampMixin):
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
