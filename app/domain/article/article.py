from typing import Optional
from pydantic import Field

from app.enums.enums import ReportState
from app.database.models.metadata_document import BaseDocument


class Article(BaseDocument):

    state: ReportState = Field(default_factory=ReportState.get_default)

    admin_comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Administrator notes or feedback about the audit",
        examples=["Please verify section 3.2", "Additional documents required"]
    )

    class Settings:
        name = "audit_submit"
        indexes = [
            "user_privy_id",
            'created_by'
        ]
