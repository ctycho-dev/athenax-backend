# app/domain/user/repository.py
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exists

from app.common.base_repository import BaseRepository
from app.domain.user.model import User
from app.domain.user.schema import (
    UserCreateSchema,
    UserCredsSchema,
    UserOutSchema,
)
from app.exceptions.exceptions import DatabaseError


class UserRepository(BaseRepository[User, UserOutSchema, UserCreateSchema]):
    """
    PostgreSQL repository for User using SQLAlchemy (async).

    Extends BaseRepository to inherit CRUD operations and adds
    convenience look-ups by e-mail and external_id.
    """

    def __init__(self) -> None:
        super().__init__(User, UserOutSchema, UserCreateSchema)

    # ---------- Custom queries ---------- #

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[UserCredsSchema]:
        """
        Return a lightweight User projection for the given e-mail.
        """
        try:
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user: Optional[User] = result.scalar_one_or_none()
            if not user:
                return None
            return UserCredsSchema.model_validate(user)
        except Exception as e:  # pragma: no cover
            raise DatabaseError(
                f"Failed to fetch user by e-mail {email}: {e}"
            ) from e

    async def email_exists(
        self,
        db: AsyncSession,
        email: str,
    ) -> bool:
        """
        Efficient ``EXISTS`` check for e-mail uniqueness.
        """
        stmt = select(
            exists().where(User.email == email)
        )
        result = await db.execute(stmt)
        return bool(result.scalar())
