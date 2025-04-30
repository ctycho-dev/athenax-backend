from typing import Optional
from pydantic import Field
from beanie import Document, Link, Update, after_event
from datetime import datetime
from app.schemas.research import ResearchSteps
from app.database.models.user import User
from app.enums.enums import ReportState


class ResearchForm(Document):

    state: ReportState = Field(default_factory=ReportState.get_default)
    user: Optional[Link[User]] = None
    steps: ResearchSteps
    user_privy_id: str

    # Admin Fields
    admin_comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Administrator notes or feedback about the audit",
        examples=["Please verify section 3.2", "Additional documents required"]
    )

    # Metadata Fields
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the audit was created",
        # frozen=True  # Prevents modification after creation
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the audit was last updated"
    )

    class Settings:
        name = "user_research"
        indexes = [
            "user_pivy_id"
        ]

    @after_event(Update)
    def update_updated_at(self):
        """Updated."""
        self.updated_at = datetime.now()
