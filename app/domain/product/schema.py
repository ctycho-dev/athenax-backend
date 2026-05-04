from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.common.schema import CamelModel
from app.domain.paper.schema import PaperSummarySchema
from app.enums.enums import (
    ProductStage, ProductStatus,
    ProductLinkType, ProductMediaType, VerificationStatus, BountyStatus,
)


class ProductCreateSchema(CamelModel):
    name: str = Field(max_length=150)
    url: str | None = Field(default=None, max_length=500)
    short_desc: str | None = Field(default=None, max_length=150)
    description: str | None = None
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    quality_badge: str | None = Field(default=None, max_length=50)
    imported: bool = False
    logo: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=200)
    backers: list[str] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    sub_category_ids: list[int] = Field(default_factory=list)


class ProductUpdateSchema(CamelModel):
    name: str | None = Field(default=None, max_length=150)
    short_desc: str | None = Field(default=None, max_length=150)
    description: str | None = None
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    quality_badge: str | None = Field(default=None, max_length=50)
    imported: bool | None = None
    logo: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=200)
    category_ids: list[int] | None = None
    sub_category_ids: list[int] | None = None


class ProductBaseSchema(CamelModel):
    id: int
    slug: str
    name: str
    short_desc: str | None
    description: str | None
    stage: ProductStage | None
    funding: float | None
    founded: int | None
    quality_badge: str | None
    imported: bool
    logo: str | None
    email: str | None
    status: ProductStatus
    vote_count: int = 0
    bookmark_count: int = 0
    investor_interest_count: int = 0
    category_ids: list[int] = Field(default_factory=list)
    sub_category_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None


class ProductSummarySchema(CamelModel):
    id: int
    slug: str
    name: str
    stage: ProductStage | None
    vote_count: int = 0
    bookmark_count: int = 0
    category_ids: list[int] = Field(default_factory=list)
    created_at: datetime


class ProductListSchema(ProductBaseSchema):
    bookmarked: bool | None = None


class FounderSummarySchema(CamelModel):
    id: int
    name: str
    lab_name: str | None = None
    university_name: str | None = None


class ProductOutSchema(ProductBaseSchema):
    papers: list[PaperSummarySchema] = Field(default_factory=list)
    founder: FounderSummarySchema | None = None
    voted: bool | None = None
    bookmarked: bool | None = None
    interested: bool | None = None
    links: list["ProductLinkOutSchema"] = Field(default_factory=list)
    media: list["ProductMediaOutSchema"] = Field(default_factory=list)
    team: list["TeamMemberOutSchema"] = Field(default_factory=list)
    backers: list["ProductBackerOutSchema"] = Field(default_factory=list)
    voices: list["ProductVoiceOutSchema"] = Field(default_factory=list)
    bounties: list["BountyOutSchema"] = Field(default_factory=list)


class ProductStatusUpdateSchema(CamelModel):
    status: ProductStatus


class VoteSchema(CamelModel):
    voted: bool


class BookmarkSchema(CamelModel):
    bookmarked: bool


class InvestorInterestSchema(CamelModel):
    interested: bool


class ToggleOutSchema(CamelModel):
    product_id: int
    count: int


class CommentCreateSchema(CamelModel):
    text: str


class CommentUpdateSchema(CamelModel):
    text: str


class CommentOutSchema(CamelModel):
    id: int
    product_id: int
    text: str
    pinned: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: int


class CommentPinSchema(CamelModel):
    pinned: bool


class ReleasePeriodSchema(CamelModel):
    total: int
    today: int
    this_week: int
    this_month: int


class ProductReleaseStatsSchema(CamelModel):
    releases: ReleasePeriodSchema


# --- Product Links ---

class ProductLinkCreateSchema(CamelModel):
    link_type: ProductLinkType
    url: str = Field(max_length=500)
    label: str | None = Field(default=None, max_length=100)


class ProductLinkUpdateSchema(CamelModel):
    url: str | None = Field(default=None, max_length=500)
    label: str | None = Field(default=None, max_length=100)


class ProductLinkOutSchema(CamelModel):
    id: int
    product_id: int
    link_type: ProductLinkType
    url: str
    label: str | None


# --- Product Media ---

class ProductMediaCreateSchema(CamelModel):
    media_type: ProductMediaType
    storage_key: str = Field(max_length=500)
    sort_order: int = 0


class ProductMediaUpdateSchema(CamelModel):
    sort_order: int | None = None


class ProductMediaOutSchema(CamelModel):
    id: int
    media_type: ProductMediaType
    sort_order: int
    url: str | None = None


# --- Team Members ---

class TeamMemberCreateSchema(CamelModel):
    user_id: int | None = None
    name: str = Field(max_length=100)
    role_label: str | None = Field(default=None, max_length=150)
    bio_note: str | None = Field(default=None, max_length=300)
    twitter_url: str | None = Field(default=None, max_length=200)
    github_url: str | None = Field(default=None, max_length=200)


class TeamMemberUpdateSchema(CamelModel):
    name: str | None = Field(default=None, max_length=100)
    role_label: str | None = Field(default=None, max_length=150)
    bio_note: str | None = Field(default=None, max_length=300)
    twitter_url: str | None = Field(default=None, max_length=200)
    github_url: str | None = Field(default=None, max_length=200)


class TeamMemberStatusUpdateSchema(CamelModel):
    status: VerificationStatus


class TeamMemberOutSchema(CamelModel):
    id: int
    product_id: int
    user_id: int | None
    name: str
    role_label: str | None
    bio_note: str | None
    twitter_url: str | None
    github_url: str | None
    status: VerificationStatus


# --- Product Backers ---

class ProductBackerCreateSchema(CamelModel):
    name: str = Field(max_length=150)


class ProductBackerOutSchema(CamelModel):
    id: int
    product_id: int
    name: str


# --- Product Voices ---

class ProductVoiceCreateSchema(CamelModel):
    quote: str
    author_handle: str = Field(max_length=100)
    author_name: str | None = Field(default=None, max_length=150)
    source_url: str | None = Field(default=None, max_length=500)
    sort_order: int = 0


class ProductVoiceUpdateSchema(CamelModel):
    quote: str | None = None
    author_handle: str | None = Field(default=None, max_length=100)
    author_name: str | None = Field(default=None, max_length=150)
    source_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None


class ProductVoiceOutSchema(CamelModel):
    id: int
    product_id: int
    quote: str
    author_handle: str
    author_name: str | None
    source_url: str | None
    sort_order: int


# --- Bounties ---

class BountyCreateSchema(CamelModel):
    title: str = Field(max_length=200)
    tech_label: str | None = Field(default=None, max_length=100)
    reward_amount: Decimal
    external_url: str = Field(max_length=500)


class BountyUpdateSchema(CamelModel):
    title: str | None = Field(default=None, max_length=200)
    tech_label: str | None = Field(default=None, max_length=100)
    reward_amount: Decimal | None = None
    status: BountyStatus | None = None
    external_url: str | None = Field(default=None, max_length=500)


class BountyOutSchema(CamelModel):
    id: int
    product_id: int
    title: str
    tech_label: str | None
    reward_amount: Decimal
    status: BountyStatus
    external_url: str
