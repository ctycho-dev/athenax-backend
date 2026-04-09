from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.enums.enums import PaperSourceType, PaperStatus, PaperVerificationStatus


class PaperSummarySchema(CamelModel):
    id: int
    title: str
    slug: str
    abstract: str | None
    published_at: datetime | None
    vote_count: int = 0


class PaperCreateSchema(CamelModel):
    product_id: int | None = None
    title: str = Field(max_length=255)
    abstract: str | None = None
    source_type: PaperSourceType
    external_url: str | None = Field(default=None, max_length=500)
    content: str | None = None
    category_ids: list[int] = Field(default_factory=list)


class PaperUpdateSchema(CamelModel):
    product_id: int | None = None
    title: str | None = Field(default=None, max_length=255)
    abstract: str | None = None
    source_type: PaperSourceType | None = None
    external_url: str | None = Field(default=None, max_length=500)
    content: str | None = None
    status: PaperStatus | None = None
    category_ids: list[int] | None = None


class PaperVerificationStatusUpdateSchema(CamelModel):
    verification_status: PaperVerificationStatus



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
    verification_status: PaperVerificationStatus = PaperVerificationStatus.PENDING
    vote_count: int = 0
    voted: bool | None = None
    category_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VoteSchema(CamelModel):
    voted: bool


class VoteOutSchema(CamelModel):
    paper_id: int
    vote_count: int
