from typing import List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer
from app.enums.enums import ArticleState


class ArticleCreate(BaseModel):

    title: str
    slug: str = Field(..., max_length=100)
    html_content: str
    type: Literal["audit", "research"]
    state: ArticleState = ArticleState.DRAFT
    related_audit_ids: List[str] = []
    related_research_ids: List[str] = []


class ArticleOut(BaseModel):
    id: str
    title: str
    slug: str
    html_content: str
    type: Literal["audit", "research"]
    state: ArticleState
    # created_by: str
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime) -> str:
        return created_at.isoformat()

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime) -> str:
        return updated_at.isoformat()

    model_config = {
        "from_attributes": True
    }
