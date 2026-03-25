from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.base_repository import BaseRepository
from app.domain.university.model import University
from app.domain.university.schema import UniversityCreateSchema, UniversityOutSchema
from app.exceptions.exceptions import DatabaseError


class UniversityRepository(BaseRepository[University, UniversityOutSchema, UniversityCreateSchema]):
    def __init__(self) -> None:
        super().__init__(University, UniversityOutSchema, UniversityCreateSchema)

    async def list_all(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[University]:
        try:
            result = await db.execute(
                select(self.model)
                .order_by(self.model.id)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to retrieve universities: {e}") from e
