from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lab.repository import LabRepository
from app.domain.lab.schema import LabCreateSchema, LabOutSchema, LabUpdateSchema
from app.domain.user.schema import UserOutSchema


class LabService:
    def __init__(self, repo: LabRepository):
        self.repo = repo

    async def create(
        self,
        db: AsyncSession,
        data: LabCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> LabOutSchema:
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
