from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.enums.enums import VerificationStatus
from app.exceptions.exceptions import NotFoundError, ValidationError


class CategoryRepository(BaseRepository[Category]):
    def __init__(self) -> None:
        super().__init__(Category)

    async def get_children(self, db: AsyncSession, parent_id: int) -> list[Category]:
        result = await db.execute(
            select(Category)
            .where(Category.parent_id == parent_id, Category.status == VerificationStatus.APPROVED.value)
            .order_by(Category.name.asc())
        )
        return list(result.scalars().all())

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

    async def assert_are_subcategories(self, db: AsyncSession, category_ids: list[int]) -> None:
        """Raise ValidationError if any given IDs are not subcategories (parent_id IS NULL)."""
        if not category_ids:
            return
        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(
            select(Category.id).where(Category.id.in_(unique_ids), Category.parent_id.is_not(None))
        )
        found_sub_ids = {row[0] for row in result.all()}
        not_sub = [cid for cid in unique_ids if cid not in found_sub_ids]
        if not_sub:
            raise ValidationError(f"Category IDs are not subcategories: {not_sub}")
