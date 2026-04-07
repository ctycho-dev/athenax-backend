from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.domain.category.schema import CategoryOutSchema
from app.enums.enums import PaperSourceType, PaperStatus


class PaperSummarySchema(CamelModel):
    id: int
    title: str
    slug: str
    published_at: datetime | None


class PaperCreateSchema(CamelModel):
    product_id: int | None = None
    title: str = Field(max_length=255)
    abstract: str | None = None
    status: PaperStatus = PaperStatus.DRAFT
    source_type: PaperSourceType
    external_url: str | None = Field(default=None, max_length=500)
    content: str | None = None
    category_ids: list[int] = Field(default_factory=list)


class PaperUpdateSchema(CamelModel):
    product_id: int | None = None
    title: str | None = Field(default=None, max_length=255)
    abstract: str | None = None
    status: PaperStatus | None = None
    source_type: PaperSourceType | None = None
    external_url: str | None = Field(default=None, max_length=500)
    content: str | None = None
    category_ids: list[int] | None = None


class PaperOutSchema(CamelModel):
    id: int
    user_id: int
    product_id: int | None
    title: str
    slug: str
    abstract: str | None
    status: PaperStatus
    published_at: datetime | None
    source_type: PaperSourceType
    external_url: str | None
    content: str | None
    vote_count: int = 0
    categories: list[CategoryOutSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VoteSchema(CamelModel):
    voted: bool


class VoteOutSchema(CamelModel):
    paper_id: int
    vote_count: int
