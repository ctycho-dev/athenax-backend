from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.user.repository import UserRepository
from app.domain.user.schema import (
    UserCreateSchema,
    UserOutSchema,
    UserCredsSchema
)
from app.core.logger import get_logger
from app.core.config import settings
from app.utils.oauth2 import hash_password
from app.enums.enums import UserRole


logger = get_logger(__name__)


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_admin_user(self, db: AsyncSession):
        user = await self.repo.get_by_email(db, settings.ADMIN_LOGIN)
        if user:
            return user

        data = UserCreateSchema(
            email=settings.ADMIN_LOGIN,
            password=hash_password(settings.ADMIN_PWD),
            role=UserRole.ADMIN,
        )
        new_user = await self.repo.create(db, data)
        return new_user
    
    async def get_all(self, db: AsyncSession) -> list[UserOutSchema]:
        users = await self.repo.get_all(db)
        return users

    async def get_by_id(self, db: AsyncSession, user_id: int) -> UserOutSchema | None:
        user = await self.repo.get_by_id(db, user_id)
        return user

    async def delete_by_id(self, db: AsyncSession, current_user: UserOutSchema, user_id: int) -> None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail='Forbidden.')
        
        if current_user.id == user_id:
            raise HTTPException(status_code=403, detail='Cannot delete yourself.')

        await self.repo.delete_by_id(db, user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> UserCredsSchema | None:
        user = await self.repo.get_by_email(db, email)
        return user

    async def create_user(self, db: AsyncSession, user: UserCreateSchema) -> UserOutSchema | None:
        existing_user = await self.repo.get_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User already exists'
            )
        
        user.password = hash_password(user.password)
        new_user = await self.repo.create(db, user)
        return new_user
