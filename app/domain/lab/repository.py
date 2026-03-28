from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.common.db_utils import sync_association
from app.domain.category.model import Category
from app.domain.category.repository import CategoryRepository
from app.domain.lab.model import Lab, LabCategory
from app.domain.lab.schema import LabCreateSchema, LabUpdateSchema
from app.exceptions.exceptions import NotFoundError


class LabRepository(BaseRepository[Lab]):
    def __init__(self, category_repo: CategoryRepository) -> None:
        super().__init__(Lab)
        self.category_repo = category_repo

    async def create_lab(
        self,
        db: AsyncSession,
        data: LabCreateSchema,
        current_user_id: int | None = None,
    ) -> Lab:
        payload = data.model_dump()
        category_ids = payload.pop("category_ids", [])
        new_category_names = payload.pop("new_categories", [])

        resolved_ids = list(category_ids)
        if category_ids:
            await self._assert_categories_exist(db, category_ids)
        if new_category_names:
            new_cats = await self.category_repo.get_or_create_by_names(db, new_category_names)
            resolved_ids += [c.id for c in new_cats]

        lab = await super().create(db, payload, current_user_id=current_user_id)
        await sync_association(db, LabCategory.__table__, "lab_id", lab.id, "category_id", set(resolved_ids))
        await db.flush()
        return lab

    async def update_lab(
        self,
        db: AsyncSession,
        _id: int,
        data: LabUpdateSchema,
        current_user_id: int | None = None,
    ) -> Lab:
        payload = data.model_dump(exclude_unset=True)
        category_ids = payload.pop("category_ids", None)

        lab = await super().update(db, _id, payload, current_user_id=current_user_id)

        if category_ids is not None:
            await self._assert_categories_exist(db, category_ids)
            await sync_association(db, LabCategory.__table__, "lab_id", _id, "category_id", set(category_ids))
            await db.flush()

        return lab

    async def get_categories_for_lab(self, db: AsyncSession, lab_id: int) -> list[Category]:
        result = await db.execute(
            select(Category)
            .join(LabCategory.__table__, Category.id == LabCategory.__table__.c.category_id)
            .where(LabCategory.__table__.c.lab_id == lab_id)
        )
        return list(result.scalars().all())

    async def _assert_categories_exist(self, db: AsyncSession, category_ids: list[int]) -> None:
        if not category_ids:
            return
        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(select(Category.id).where(Category.id.in_(unique_ids)))
        found_ids = {row[0] for row in result.all()}
        missing = [cid for cid in unique_ids if cid not in found_ids]
        if missing:
            raise NotFoundError(f"Category IDs not found: {missing}")
