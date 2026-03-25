# app/domain/user/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exists

from app.common.base_repository import BaseRepository
from app.domain.user.model import User
from app.domain.user.schema import UserCreateDBSchema, UserOutSchema
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

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> User | None:
        """
        Return the user model for the given e-mail.
        """
        try:
            result = await db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to fetch user by e-mail {email}: {e}") from e

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
    ) -> User | None:
        try:
            result = await db.execute(select(User).where(User.reset_hash == reset_hash))
            return result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to fetch user by reset hash: {e}") from e

    async def get_by_verification_hash(
        self,
        db: AsyncSession,
        verification_hash: str,
    ) -> User | None:
        try:
            result = await db.execute(
                select(User).where(User.verification_hash == verification_hash)
            )
            return result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to fetch user by verification hash: {e}") from e
