from typing import Optional
from pydantic import Field

from app.domain.submit.research.schema import (
    ResearchSteps,
    Comment
)
from app.enums.enums import ReportState
from app.common.metadata_document import BaseDocument


class ResearchSubmit(BaseDocument):

    state: ReportState = Field(default_factory=ReportState.get_default)
    steps: ResearchSteps
    user_privy_id: str

    comments: list[Comment] = Field(default_factory=list)

    class Settings:
        name = "research_submit"
        indexes = [
            "user_privy_id",
            'created_by'
        ]
