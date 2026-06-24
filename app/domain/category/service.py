from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.cache_keys import CATEGORY_LIST_PREFIX
from app.domain.category.model import Category
from app.domain.category.repository import CategoryRepository
from app.domain.category.schema import CategoryCreateSchema, CategoryStatusUpdateSchema, CategoryUpdateSchema
from app.domain.user.schema import UserOutSchema
from app.enums.enums import VerificationStatus
from app.exceptions.exceptions import NotFoundError
from app.infrastructure.redis.client import RedisClient


class CategoryService:
    def __init__(self, repo: CategoryRepository, redis: RedisClient | None = None):
        self.repo = repo
        self.redis = redis

    async def get_by_name(self, db: AsyncSession, name: str, *, is_subcategory: bool) -> Category:
        category = await self.repo.get_by_name(db, name, is_subcategory=is_subcategory)
        if category is None:
            label = "Subcategory" if is_subcategory else "Category"
            raise NotFoundError(f"{label} '{name}' not found")
        return category

    async def _invalidate_list_cache(self) -> None:
        if self.redis:
            await self.redis.delete_by_pattern(f"{CATEGORY_LIST_PREFIX}:*")

    async def create(
        self,
        db: AsyncSession,
        data: CategoryCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> Category:
        result = await self.repo.create(db, data, current_user_id=current_user.id if current_user else None)
        await db.commit()
        await self._invalidate_list_cache()
        return result

    async def list(self, db: AsyncSession, limit: int, offset: int, parent_id: int | None = None) -> list[Category]:
        if parent_id is not None:
            await self.repo.assert_exists_by_id(db, parent_id)
            return await self.repo.get_children(db, parent_id)
        result = await db.execute(
            select(Category)
            .where(Category.parent_id.is_(None), Category.status == VerificationStatus.APPROVED.value)
            .order_by(Category.name.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        category_id: int,
        data: CategoryStatusUpdateSchema,
        current_user: UserOutSchema,
    ) -> Category:
        category = await self.repo.get_by_id(db, category_id)
        await self.repo.update_instance(db, category, {"status": data.status.value})
        await db.commit()
        await db.refresh(category)
        await self._invalidate_list_cache()
        return category

    async def get_by_id(self, db: AsyncSession, category_id: int) -> Category:
        return await self.repo.get_by_id(db, category_id)

    async def update(
        self,
        db: AsyncSession,
        category_id: int,
        data: CategoryUpdateSchema,
        current_user: UserOutSchema | None = None,
    ) -> Category:
        result = await self.repo.update(db, category_id, data, current_user_id=current_user.id if current_user else None)
        await db.commit()
        await self._invalidate_list_cache()
        return result

    async def delete_by_id(
        self,
        db: AsyncSession,
        category_id: int,
        current_user: UserOutSchema | None = None,
    ) -> None:
        await self.repo.delete_by_id(db, category_id)
        await db.commit()
        await self._invalidate_list_cache()

