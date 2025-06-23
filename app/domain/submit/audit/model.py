from pydantic import Field

from app.domain.submit.audit.schema import (
    AuditSteps,
    Comment
)
from app.enums.enums import ReportState
from app.common.metadata_document import BaseDocument


class AuditSubmit(BaseDocument):

    state: ReportState = Field(default_factory=ReportState.get_default)
    steps: AuditSteps
    user_privy_id: str

    comments: list[Comment] = Field(default_factory=list)

    class Settings:
        name = "audit_submit"
        indexes = [
            "user_privy_id",
            'created_by'
        ]
