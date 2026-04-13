from sqlalchemy import String, Integer, Float, Text, Boolean, ForeignKey, Enum as SQLEnum, PrimaryKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin
from app.enums.enums import ProductStage, ProductStatus


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_category"
    __table_args__ = (PrimaryKeyConstraint("product_id", "category_id"),)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )


class ProductVote(Base, TimestampMixin):
    __tablename__ = "product_votes"
    __table_args__ = (PrimaryKeyConstraint("product_id", "user_id"),)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ProductBookmark(Base, TimestampMixin):
    __tablename__ = "product_bookmarks"
    __table_args__ = (PrimaryKeyConstraint("product_id", "user_id"),)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ProductInvestorInterest(Base, TimestampMixin):
    __tablename__ = "product_investor_interests"
    __table_args__ = (PrimaryKeyConstraint("product_id", "user_id"),)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ProductComment(Base, TimestampMixin):
    __tablename__ = "product_comments"
    __table_args__ = (
        Index("ix_product_comments_product_id", "product_id"),
        Index("ix_product_comments_user_id", "user_id"),
        Index("ix_product_comments_product_created", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column("desc", Text, nullable=True)
    stage: Mapped[ProductStage | None] = mapped_column(
        SQLEnum(ProductStage, name="product_stage", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    funding: Mapped[float | None] = mapped_column(Float, nullable=True)
    founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github: Mapped[str | None] = mapped_column(String(200), nullable=True)
    demo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quality_badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imported: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    twitter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        SQLEnum(ProductStatus, name="product_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default="pending",
    )
