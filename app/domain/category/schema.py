from app.common.schema import CamelModel
from app.enums.enums import VerificationStatus


class CategoryCreateSchema(CamelModel):
    name: str
    parent_id: int | None = None


class CategoryUpdateSchema(CamelModel):
    name: str


class CategoryStatusUpdateSchema(CamelModel):
    status: VerificationStatus


class CategoryOutSchema(CamelModel):
    id: int
    name: str
    parent_id: int | None = None
    status: str = VerificationStatus.APPROVED.value
