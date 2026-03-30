from datetime import datetime

from pydantic import Field

from app.common.schema import CamelModel
from app.domain.category.schema import CategoryOutSchema


class LabBaseSchema(CamelModel):
    university_id: int
    name: str = Field(max_length=150)
    focus: str | None = Field(default=None, max_length=255)
    description: str | None = None
    active: bool = True


class LabCreateSchema(LabBaseSchema):
    category_ids: list[int] = Field(default_factory=list)


class LabUpdateSchema(CamelModel):
    university_id: int | None = None
    name: str | None = Field(default=None, max_length=150)
    focus: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category_ids: list[int] | None = None
    active: bool | None = None


class LabOutSchema(LabBaseSchema):
    id: int
    categories: list[CategoryOutSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
