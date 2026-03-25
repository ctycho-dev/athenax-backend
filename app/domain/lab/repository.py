from app.common.base_repository import BaseRepository
from app.domain.lab.model import Lab
from app.domain.lab.schema import LabCreateSchema, LabOutSchema


class LabRepository(BaseRepository[Lab, LabOutSchema, LabCreateSchema]):
    def __init__(self) -> None:
        super().__init__(Lab, LabOutSchema, LabCreateSchema)
