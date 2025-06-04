from pydantic import BaseModel
from typing import Optional


class StoredFile(BaseModel):
    """File schema."""

    bucket: str
    key: str
    original_filename: str
    content_type: str
    url: Optional[str]
