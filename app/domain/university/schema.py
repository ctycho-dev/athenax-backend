from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel


class UniversityBaseSchema(CamelModel):
    name: str
    country: str = Field(min_length=3, max_length=3)
    focus: str | None = None


class UniversityCreateSchema(UniversityBaseSchema):
    pass


class UniversityUpdateSchema(CamelModel):
    name: str | None = None
    country: str | None = Field(default=None, min_length=3, max_length=3)
    focus: str | None = None


class UniversityOutSchema(UniversityBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
