from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.domain.lab.model import Lab, LabCategory


class LabRepository(BaseRepository[Lab]):
    def __init__(self) -> None:
        super().__init__(Lab)

    async def get_categories_for_lab(self, db: AsyncSession, lab_id: int) -> list[Category]:
        result = await db.execute(
            select(Category)
            .join(LabCategory.__table__, Category.id == LabCategory.__table__.c.category_id)
            .where(LabCategory.__table__.c.lab_id == lab_id)
        )
        return list(result.scalars().all())

