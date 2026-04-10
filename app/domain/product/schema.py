from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.domain.paper.schema import PaperSummarySchema
from app.enums.enums import ProductStage, ProductStatus


class ProductCreateSchema(CamelModel):
    name: str = Field(max_length=150)
    description: str | None = None
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    github: str | None = Field(default=None, max_length=200)
    demo: str | None = Field(default=None, max_length=200)
    quality_badge: str | None = Field(default=None, max_length=50)
    category_ids: list[int] = Field(default_factory=list)


class ProductUpdateSchema(CamelModel):
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    github: str | None = Field(default=None, max_length=200)
    demo: str | None = Field(default=None, max_length=200)
    quality_badge: str | None = Field(default=None, max_length=50)
    category_ids: list[int] | None = None


class ProductBaseSchema(CamelModel):
    id: int
    user_id: int | None
    slug: str
    name: str
    description: str | None
    stage: ProductStage | None
    funding: float | None
    founded: int | None
    github: str | None
    demo: str | None
    quality_badge: str | None
    status: ProductStatus
    vote_count: int = 0
    bookmark_count: int = 0
    investor_interest_count: int = 0
    category_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


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
    user_id: int
    text: str
    created_at: datetime
    updated_at: datetime


class ReleasePeriodSchema(CamelModel):
    total: int
    today: int
    this_week: int
    this_month: int


class ProductReleaseStatsSchema(CamelModel):
    releases: ReleasePeriodSchema
