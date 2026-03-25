from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lab.repository import LabRepository
from app.domain.lab.schema import LabCreateSchema, LabOutSchema, LabUpdateSchema
from app.domain.university.repository import UniversityRepository
from app.domain.user.schema import UserOutSchema
from app.exceptions.exceptions import NotFoundError


class LabService:
    def __init__(self, repo: LabRepository):
        self.repo = repo

    async def create(
        self,
        db: AsyncSession,
        data: LabCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
        await self._ensure_university_exists(db, data.university_id)
        return await self.repo.create(
            db,
            data,
            current_user_id=current_user.id if current_user else None,
        )

    async def list(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LabOutSchema]:
        labs = await self.repo.list_all(db, limit=limit, offset=offset)
        return [LabOutSchema.model_validate(lab) for lab in labs]

    async def get_by_id(self, db: AsyncSession, lab_id: int) -> LabOutSchema:
        lab = await self.repo.get_by_id(db, lab_id)
        return cast(LabOutSchema, lab)

    async def update(
        self,
        db: AsyncSession,
        lab_id: int,
        data: LabUpdateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
        if data.university_id is not None:
            await self._ensure_university_exists(db, data.university_id)
        return await self.repo.update(
            db,
            lab_id,
            data,
            current_user_id=current_user.id if current_user else None,
        )

    async def delete_by_id(
        self,
        db: AsyncSession,
        lab_id: int,
        current_user: UserOutSchema | None = None,
    ) -> None:
        await self.repo.delete_by_id(db, lab_id)

    async def _ensure_university_exists(self, db: AsyncSession, university_id: int) -> None:
        try:
            await UniversityRepository().get_by_id(db, university_id)
        except NotFoundError as exc:
            raise NotFoundError(
                f"University with ID {university_id} not found"
            ) from exc
