from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.category.model import Category
from app.domain.category.repository import CategoryRepository
from app.domain.category.schema import CategoryCreateSchema, CategoryUpdateSchema
from app.domain.user.schema import UserOutSchema


class CategoryService:
    def __init__(self, repo: CategoryRepository):
        self.repo = repo

    async def create(
        self,
        db: AsyncSession,
        data: CategoryCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> Category:
        result = await self.repo.create(db, data, current_user_id=current_user.id if current_user else None)
        await db.commit()
        return result

    async def list(self, db: AsyncSession, limit: int, offset: int) -> list[Category]:
        return await self.repo.get_all(db, limit=limit, offset=offset)

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
        return result

    async def delete_by_id(
        self,
        db: AsyncSession,
        category_id: int,
        current_user: UserOutSchema | None = None,
    ) -> None:
        await self.repo.delete_by_id(db, category_id)
        await db.commit()
