# app/domain/user/repository.py
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exists

from app.common.base_repository import BaseRepository
from app.domain.user.model import User
from app.domain.user.schema import (
    UserCreateDBSchema,
    UserCredsSchema,
    UserOutSchema,
)
from app.exceptions.exceptions import DatabaseError


class UserRepository(BaseRepository[User, UserOutSchema, UserCreateDBSchema]):
    """
    PostgreSQL repository for User using SQLAlchemy (async).

    Extends BaseRepository to inherit CRUD operations and adds
    convenience look-ups by e-mail and external_id.
    """

    def __init__(self) -> None:
        super().__init__(User, UserOutSchema, UserCreateDBSchema)

    # ---------- Custom queries ---------- #

    async def _get_user_by_column(
        self,
        db: AsyncSession,
        column_name: str,
        value: str,
        response_schema: type[Any],
        error_message: str,
    ) -> Any | None:
        try:
            column = getattr(User, column_name)
            result = await db.execute(select(User).where(column == value))
            user: Optional[User] = result.scalar_one_or_none()
            if not user:
                return None
            return response_schema.model_validate(user)
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"{error_message}: {e}") from e

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[UserCredsSchema]:
        """
        Return a lightweight User projection for the given e-mail.
        """
        return await self._get_user_by_column(
            db=db,
            column_name="email",
            value=email,
            response_schema=UserCredsSchema,
            error_message=f"Failed to fetch user by e-mail {email}",
        )

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

    async def get_by_reset_hash(
        self,
        db: AsyncSession,
        reset_hash: str,
    ) -> Optional[UserOutSchema]:
        return await self._get_user_by_column(
            db=db,
            column_name="reset_hash",
            value=reset_hash,
            response_schema=UserOutSchema,
            error_message="Failed to fetch user by reset hash",
        )

    async def get_by_verification_hash(
        self,
        db: AsyncSession,
        verification_hash: str,
    ) -> Optional[UserOutSchema]:
        return await self._get_user_by_column(
            db=db,
            column_name="verification_hash",
            value=verification_hash,
            response_schema=UserOutSchema,
            error_message="Failed to fetch user by verification hash",
        )
