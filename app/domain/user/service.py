from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.user.repository import UserRepository
from app.domain.user.schema import (
    UserSignupSchema,
    UserCreateDBSchema,
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

    async def create_admin_user(
        self,
        db: AsyncSession,
    ) -> UserCredsSchema | UserOutSchema:
        user = await self.repo.get_by_email(db, settings.ADMIN_LOGIN)
        if user:
            return user

        data = UserCreateDBSchema(
            name="Admin",
            email=settings.ADMIN_LOGIN,
            password_hash=hash_password(settings.ADMIN_PWD),
            role=UserRole.USER,
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
        await self.repo.delete_by_id(db, user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> UserCredsSchema | None:
        user = await self.repo.get_by_email(db, email)
        return user

    async def create_user(self, db: AsyncSession, user: UserSignupSchema) -> UserOutSchema:
        existing_user = await self.repo.get_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User already exists'
            )

        data = UserCreateDBSchema(
            name=user.name,
            email=user.email,
            password_hash=hash_password(user.password),
            role=user.role,
            external_id=user.external_id,
            lab_id=user.lab_id,
            bio=user.bio,
            organization=user.organization,
        )
        new_user = await self.repo.create(db, data)
        return new_user

    async def signup_user(self, db: AsyncSession, user: UserSignupSchema) -> UserOutSchema:
        """
        Public signup path.

        Force the default user role so the client cannot self-assign elevated roles.
        """
        signup_data = user.model_copy(update={"role": UserRole.USER})
        return await self.create_user(db, signup_data)
