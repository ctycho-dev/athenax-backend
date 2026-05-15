from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.tag.model import Tag


class TagRepository(BaseRepository[Tag]):
    def __init__(self) -> None:
        super().__init__(Tag)

    async def get_by_names(self, db: AsyncSession, names: list[str]) -> list[Tag]:
        if not names:
            return []
        lower_names = [n.lower() for n in names]
        result = await db.execute(select(Tag).where(func.lower(Tag.name).in_(lower_names)))
        return list(result.scalars().all())
