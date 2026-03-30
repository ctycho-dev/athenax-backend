from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.exceptions.exceptions import NotFoundError


class CategoryRepository(BaseRepository[Category]):
    def __init__(self) -> None:
        super().__init__(Category)

    async def assert_exist(self, db: AsyncSession, category_ids: list[int]) -> None:
        """Raise NotFoundError if any of the given category IDs do not exist."""
        if not category_ids:
            return
        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(select(Category.id).where(Category.id.in_(unique_ids)))
        found_ids = {row[0] for row in result.all()}
        missing = [cid for cid in unique_ids if cid not in found_ids]
        if missing:
            raise NotFoundError(f"Category IDs not found: {missing}")
