from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lab.repository import LabRepository
from app.domain.category.schema import CategoryOutSchema
from app.domain.lab.schema import LabCreateSchema, LabOutSchema, LabUpdateSchema
from app.domain.university.repository import UniversityRepository
from app.domain.user.schema import UserOutSchema
from app.exceptions.exceptions import NotFoundError


class LabService:
    def __init__(self, repo: LabRepository, university_repo: UniversityRepository):
        self.repo = repo
        self.university_repo = university_repo

    async def create(
        self,
        db: AsyncSession,
        data: LabCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
        await self._ensure_university_exists(db, data.university_id)
        lab = await self.repo.create_lab(db, data, current_user_id=current_user.id if current_user else None)
        await db.commit()
        await db.refresh(lab)
        return await self._to_schema(db, lab)

    async def list(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LabOutSchema]:
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
        lab = await self.repo.update_lab(db, lab_id, data, current_user_id=current_user.id if current_user else None)
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
