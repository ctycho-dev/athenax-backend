from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.domain.category.schema import CategoryOutSchema
from app.enums.enums import ProductSector, ProductStage


class ProductCreateSchema(CamelModel):
    slug: str = Field(max_length=150)
    name: str = Field(max_length=150)
    description: str | None = None
    sector: ProductSector
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    github: str | None = Field(default=None, max_length=200)
    demo: str | None = Field(default=None, max_length=200)
    quality_badge: str | None = Field(default=None, max_length=50)
    category_ids: list[int] = Field(default_factory=list)


class ProductUpdateSchema(CamelModel):
    slug: str | None = Field(default=None, max_length=150)
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    sector: ProductSector | None = None
    stage: ProductStage | None = None
    funding: float | None = None
    founded: int | None = None
    github: str | None = Field(default=None, max_length=200)
    demo: str | None = Field(default=None, max_length=200)
    quality_badge: str | None = Field(default=None, max_length=50)
    category_ids: list[int] | None = None


class ProductOutSchema(CamelModel):
    id: int
    user_id: int | None
    slug: str
    name: str
    description: str | None
    sector: ProductSector
    stage: ProductStage | None
    funding: float | None
    founded: int | None
    github: str | None
    demo: str | None
    quality_badge: str | None
    vote_count: int = 0
    bookmark_count: int = 0
    investor_interest_count: int = 0
    categories: list[CategoryOutSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


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
