from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.enums.enums import VerificationStatus
from app.exceptions.exceptions import NotFoundError, ValidationError


class CategoryRepository(BaseRepository[Category]):
    def __init__(self) -> None:
        super().__init__(Category)

    async def get_by_name(
        self, db: AsyncSession, name: str, *, is_subcategory: bool
    ) -> Category | None:
        """Exact, case-insensitive lookup. is_subcategory=True restricts to children (parent_id set)."""
        parent_filter = Category.parent_id.is_not(None) if is_subcategory else Category.parent_id.is_(None)
        result = await db.execute(
            select(Category).where(func.lower(Category.name) == name.lower(), parent_filter)
        )
        return result.scalars().first()

    async def get_children(self, db: AsyncSession, parent_id: int) -> list[Category]:
        result = await db.execute(
            select(Category)
            .where(Category.parent_id == parent_id, Category.status == VerificationStatus.APPROVED.value)
            .order_by(Category.name.asc())
        )
        return list(result.scalars().all())

    async def set_status_by_ids(
        self, db: AsyncSession, category_ids: list[int], status: str
    ) -> None:
        """Bulk status update — one set-based UPDATE instead of a per-row loop."""
        if not category_ids:
            return
        await db.execute(
            update(Category)
            .where(Category.id.in_(category_ids))
            .values(status=status)
        )

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

    async def assert_are_parent_categories(self, db: AsyncSession, category_ids: list[int]) -> None:
        """Raise ValidationError if any given IDs are subcategories (parent_id IS NOT NULL)."""
        if not category_ids:
            return
        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(
            select(Category.id).where(Category.id.in_(unique_ids), Category.parent_id.is_not(None))
        )
        sub_ids = [row[0] for row in result.all()]
        if sub_ids:
            raise ValidationError(f"Only parent categories are allowed. These are subcategories: {sub_ids}")

    async def assert_subcategories_belong_to_parents(
        self, db: AsyncSession, sub_category_ids: list[int], parent_ids: list[int]
    ) -> None:
        """Raise ValidationError if any subcategory's parent_id is not among parent_ids."""
        if not sub_category_ids:
            return
        unique_ids = list(dict.fromkeys(sub_category_ids))
        result = await db.execute(
            select(Category.id).where(Category.id.in_(unique_ids), Category.parent_id.in_(parent_ids))
        )
        valid_ids = {row[0] for row in result.all()}
        mismatched = [cid for cid in unique_ids if cid not in valid_ids]
        if mismatched:
            raise ValidationError(f"Sub-category IDs do not belong to the selected parent categories: {mismatched}")
