from sqlalchemy import String, Integer, Float, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin
from app.enums.enums import ProductSector, ProductStage


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column("desc", Text, nullable=True)
    sector: Mapped[ProductSector] = mapped_column(
        SQLEnum(ProductSector, name="product_sector"),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[ProductStage | None] = mapped_column(
        SQLEnum(ProductStage, name="product_stage"),
        nullable=True,
    )
    funding: Mapped[float | None] = mapped_column(Float, nullable=True)
    founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github: Mapped[str | None] = mapped_column(String(200), nullable=True)
    demo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quality_badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
