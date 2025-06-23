from datetime import datetime
from typing import Optional
from pydantic import Field
from beanie import Document, Link
from app.domain.user.model import User


class BaseDocument(Document):
    """
    Base document model with common metadata fields
    All application models should inherit from this
    """
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was created"
    )
    created_by: Optional[Link[User]] = Field(
        default=None,
        description="User who created the record"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was last updated"
    )
    updated_by: Optional[Link[User]] = Field(
        default=None,
        description="User who last updated the record"
    )

    class Meta:
        abstract = True  # This ensures this class won't create a collection
