from app.common.schema import CamelModel


class CategoryCreateSchema(CamelModel):
    name: str


class CategoryUpdateSchema(CamelModel):
    name: str


class CategoryOutSchema(CamelModel):
    id: int
    name: str
    parent_id: int | None = None
