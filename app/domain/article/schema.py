from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.enums.enums import ArticleStatus, ArticleType


class ArticleCreateSchema(CamelModel):
    title: str = Field(max_length=255)
    article_type: ArticleType
    content: str | None = None
    status: ArticleStatus = ArticleStatus.DRAFT
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class ArticleUpdateSchema(CamelModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    article_type: ArticleType | None = None
    content: str | None = None
    status: ArticleStatus | None = None
    published_at: datetime | None = None
    tags: list[str] | None = None


class ArticleOutSchema(CamelModel):
    id: int
    title: str
    slug: str
    article_type: ArticleType
    content: str | None
    status: ArticleStatus
    published_at: datetime | None
    creator_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ArticleSummarySchema(CamelModel):
    id: int
    title: str
    slug: str
    article_type: ArticleType
    status: ArticleStatus
    published_at: datetime | None
    creator_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
