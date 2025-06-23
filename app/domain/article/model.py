from typing import List, Literal
from pydantic import Field
from beanie import Link
from app.common.metadata_document import BaseDocument
from app.domain.submit.audit.model import AuditSubmit
from app.domain.submit.research.model import ResearchSubmit
from app.enums.enums import ArticleState


class Article(BaseDocument):

    title: str
    slug: str = Field(max_length=100)
    html_content: str
    type: Literal["audit", "research"]
    state: ArticleState = Field(default=ArticleState.DRAFT)

    related_audits: List[Link[AuditSubmit]] = []
    related_researches: List[Link[ResearchSubmit]] = []

    class Settings:
        name = "articles"
        indexes = ["slug", "type", "state", "created_by"]
