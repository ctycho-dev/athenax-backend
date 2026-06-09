from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.enums.enums import BroadcastStatus, BroadcastType


class BroadcastCreateSchema(CamelModel):
    title: str = Field(max_length=255)
    broadcast_type: BroadcastType
    status: BroadcastStatus = BroadcastStatus.DRAFT
    embed_url: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    origin_date: datetime | None = None
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class BroadcastUpdateSchema(CamelModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    broadcast_type: BroadcastType | None = None
    status: BroadcastStatus | None = None
    embed_url: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    origin_date: datetime | None = None
    published_at: datetime | None = None
    tags: list[str] | None = None


class BroadcastOutSchema(CamelModel):
    id: int
    title: str
    slug: str
    broadcast_type: BroadcastType
    status: BroadcastStatus
    embed_url: str | None
    description: str | None
    thumbnail_url: str | None
    origin_date: datetime | None
    published_at: datetime | None
    creator_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BroadcastSummarySchema(CamelModel):
    """List-path schema — omits the large `description` body."""

    id: int
    title: str
    slug: str
    broadcast_type: BroadcastType
    status: BroadcastStatus
    origin_date: datetime | None
    published_at: datetime | None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
