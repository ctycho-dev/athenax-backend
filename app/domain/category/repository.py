from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category


class CategoryRepository(BaseRepository[Category]):
    def __init__(self) -> None:
        super().__init__(Category)

    async def get_or_create_by_names(self, db: AsyncSession, names: list[str]) -> list[Category]:
        unique_names = list(dict.fromkeys(names))
        result = await db.execute(select(Category).where(Category.name.in_(unique_names)))
        existing = {c.name: c for c in result.scalars().all()}

        for name in unique_names:
            if name not in existing:
                existing[name] = await super().create(db, {"name": name})

        return [existing[name] for name in unique_names]
