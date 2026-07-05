from decimal import Decimal

from sqlalchemy import String, Integer, Float, Numeric, Text, Boolean, ForeignKey, Enum as SQLEnum, PrimaryKeyConstraint, Index, UniqueConstraint, cast
from sqlalchemy.types import UserDefinedType
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.common.audit_mixin import TimestampMixin, UserAuditMixin, SoftDeleteMixin
from app.enums.enums import ProductStage, ProductStatus, ProductLinkType, ProductMediaType, VerificationStatus, BountyStatus


class LtreeType(UserDefinedType):
    """PostgreSQL ltree extension type. Stored as ltree in DB, returned as str in Python."""
    cache_ok = True

    def get_col_spec(self, **kw):
        return "ltree"

    def bind_expression(self, bindvalue):
        # Explicitly cast bound params to ltree so asyncpg sends them as text
        return cast(bindvalue, self)

    def column_expression(self, colexpr):
        return cast(colexpr, String)

    def bind_processor(self, dialect):
        def process(value):
            return str(value) if value is not None else None
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def coerce_compared_value(self, op, value):
        return self


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
    __table_args__ = (
        PrimaryKeyConstraint("product_id", "user_id"),
        # PK leads with product_id; this serves user-scoped lookups (/me/voted) by user_id + recency.
        Index("ix_product_votes_user_created", "user_id", "created_at"),
    )

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ProductBookmark(Base, TimestampMixin):
    __tablename__ = "product_bookmarks"
    __table_args__ = (
        PrimaryKeyConstraint("product_id", "user_id"),
        # Serves /me/bookmarked (filter by user_id, order by recency).
        Index("ix_product_bookmarks_user_created", "user_id", "created_at"),
    )

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


class ProductComment(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_comments"
    __table_args__ = (
        Index("ix_product_comments_product_id", "product_id"),
        Index("ix_product_comments_product_created", "product_id", "created_at"),
        Index("ix_product_comments_path_gist", "path", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_comments.id", ondelete="CASCADE", name="fk_product_comments_parent"), nullable=True
    )
    path: Mapped[str | None] = mapped_column(LtreeType, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class Product(Base, TimestampMixin, UserAuditMixin, SoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (
        # Dominant browse path: filter by status, order by created_at (btree scanned backward for DESC).
        Index("ix_products_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
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
    short_desc: Mapped[str | None] = mapped_column(String(250), nullable=True)
    quality_badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imported: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        SQLEnum(ProductStatus, name="product_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default="pending",
    )


class ProductLink(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_links"
    __table_args__ = (
        UniqueConstraint("product_id", "link_type", name="uq_product_links_product_link_type"),
        Index("ix_product_links_product_id", "product_id"),
        Index("ix_product_links_type", "product_id", "link_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[ProductLinkType] = mapped_column(
        SQLEnum(ProductLinkType, name="product_link_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ProductMedia(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_media"
    __table_args__ = (
        Index("ix_product_media_product_id", "product_id"),
        Index("ix_product_media_sort", "product_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    media_type: Mapped[ProductMediaType] = mapped_column(
        SQLEnum(ProductMediaType, name="product_media_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class ProductTeamMember(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_team"
    __table_args__ = (
        Index("ix_product_team_product_id", "product_id"),
        Index("ix_product_team_status", "product_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bio_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    other_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus, name="team_member_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default="pending",
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProductBacker(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_backers"
    __table_args__ = (
        Index("ix_product_backers_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class ProductGrant(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_grants"
    __table_args__ = (
        Index("ix_product_grants_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class ProductVoice(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "product_voices"
    __table_args__ = (
        Index("ix_product_voices_product_id", "product_id"),
        Index("ix_product_voices_sort", "product_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    author_handle: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class Bounty(Base, TimestampMixin, UserAuditMixin):
    __tablename__ = "bounties"
    __table_args__ = (
        Index("ix_bounties_product_id", "product_id"),
        Index("ix_bounties_status", "product_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tech_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BountyStatus] = mapped_column(
        SQLEnum(BountyStatus, name="bounty_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default="open",
    )
    external_url: Mapped[str] = mapped_column(String(500), nullable=False)
