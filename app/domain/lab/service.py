from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_association
from app.domain.category.repository import CategoryRepository
from app.domain.category.schema import CategoryOutSchema
from app.domain.lab.model import LabCategory
from app.domain.lab.repository import LabRepository
from app.domain.lab.schema import LabCreateSchema, LabOutSchema, LabUpdateSchema
from app.domain.university.repository import UniversityRepository
from app.domain.user.schema import UserOutSchema
from app.exceptions.exceptions import NotFoundError


class LabService:
    def __init__(self, repo: LabRepository, university_repo: UniversityRepository, category_repo: CategoryRepository):
        self.repo = repo
        self.university_repo = university_repo
        self.category_repo = category_repo

    async def create(
        self,
        db: AsyncSession,
        data: LabCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
        await self._ensure_university_exists(db, data.university_id)

        payload = data.model_dump()
        category_ids = payload.pop("category_ids", [])

        if category_ids:
            await self.category_repo.assert_exist(db, category_ids)

        lab = await self.repo.create(db, payload, current_user_id=current_user.id if current_user else None)
        await sync_association(db, LabCategory.__table__, "lab_id", lab.id, "category_id", set(category_ids))

        await db.commit()
        await db.refresh(lab)
        return await self._to_schema(db, lab)

    async def list(self, db: AsyncSession, limit: int, offset: int) -> list[LabOutSchema]:
        labs = await self.repo.get_all(db, limit=limit, offset=offset)
        return [await self._to_schema(db, lab) for lab in labs]

    async def get_by_id(self, db: AsyncSession, lab_id: int) -> LabOutSchema:
        lab = await self.repo.get_by_id(db, lab_id)
        return await self._to_schema(db, lab)

    async def update(
        self,
        db: AsyncSession,
        lab_id: int,
        data: LabUpdateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
        if data.university_id is not None:
            await self._ensure_university_exists(db, data.university_id)

        payload = data.model_dump(exclude_unset=True)
        category_ids = payload.pop("category_ids", None)

        lab = await self.repo.update(db, lab_id, payload, current_user_id=current_user.id if current_user else None)

        if category_ids is not None:
            await self.category_repo.assert_exist(db, category_ids)
            await sync_association(db, LabCategory.__table__, "lab_id", lab_id, "category_id", set(category_ids))

        await db.commit()
        await db.refresh(lab)
        return await self._to_schema(db, lab)

    async def delete_by_id(
        self,
        db: AsyncSession,
        lab_id: int,
        current_user: UserOutSchema | None = None,
    ) -> None:
        await self.repo.delete_by_id(db, lab_id)
        await db.commit()

    async def _to_schema(self, db: AsyncSession, lab) -> LabOutSchema:
        categories = await self.repo.get_categories_for_lab(db, lab.id)
        result = LabOutSchema.model_validate(lab, from_attributes=True)
        result.categories = [CategoryOutSchema.model_validate(c, from_attributes=True) for c in categories]
        return result

    async def _ensure_university_exists(self, db: AsyncSession, university_id: int) -> None:
        try:
            await self.university_repo.get_by_id(db, university_id)
        except NotFoundError as exc:
            raise NotFoundError(f"University with ID {university_id} not found") from exc
