from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.base_repository import BaseRepository
from app.domain.lab.model import Lab
from app.domain.lab.schema import LabCreateSchema, LabOutSchema
from app.exceptions.exceptions import DatabaseError


class LabRepository(BaseRepository[Lab, LabOutSchema, LabCreateSchema]):
    def __init__(self) -> None:
        super().__init__(Lab, LabOutSchema, LabCreateSchema)

    async def list_all(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lab]:
        try:
            result = await db.execute(
                select(self.model)
                .order_by(self.model.id)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to retrieve labs: {e}") from e
