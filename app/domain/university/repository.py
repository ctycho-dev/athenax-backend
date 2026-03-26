from app.common.base_repository import BaseRepository
from app.domain.university.model import University
from app.domain.university.schema import UniversityCreateSchema, UniversityOutSchema


class UniversityRepository(BaseRepository[University]):
    def __init__(self) -> None:
        super().__init__(University)
