from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.university.repository import UniversityRepository
from app.domain.university.schema import (
    UniversityCreateSchema,
    UniversityOutSchema,
    UniversityUpdateSchema,
)
from app.domain.user.schema import UserOutSchema


class UniversityService:
    def __init__(self, repo: UniversityRepository):
        self.repo = repo

    async def create(
        self,
        db: AsyncSession,
        data: UniversityCreateSchema,
        current_user: UserOutSchema | None = None,
    ) -> UniversityOutSchema:
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
    ) -> list[UniversityOutSchema]:
        universities = await self.repo.list_all(db, limit=limit, offset=offset)
        return [UniversityOutSchema.model_validate(university) for university in universities]

    async def get_by_id(self, db: AsyncSession, university_id: int) -> UniversityOutSchema:
        university = await self.repo.get_by_id(db, university_id)
        return cast(UniversityOutSchema, university)

    async def update(
        self,
        db: AsyncSession,
        university_id: int,
        data: UniversityUpdateSchema,
        current_user: UserOutSchema | None = None,
    ) -> UniversityOutSchema:
        return await self.repo.update(
            db,
            university_id,
            data,
            current_user_id=current_user.id if current_user else None,
        )

    async def delete_by_id(
        self,
        db: AsyncSession,
        university_id: int,
        current_user: UserOutSchema | None = None,
    ) -> None:
        await self.repo.delete_by_id(db, university_id)
