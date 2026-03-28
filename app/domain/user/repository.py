# app/domain/user/repository.py
from typing import Generic, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exists, delete

from app.common.base_repository import BaseRepository
from app.common.db_utils import sync_association
from app.domain.user.model import (
    User,
    InvestorProfile,
    ResearcherProfile,
    SponsorProfile,
    UserCategory,
)
from app.enums.enums import TokenType
from app.exceptions.exceptions import DatabaseError

P = TypeVar("P")


class ProfileRepository(Generic[P]):
    """Generic repository for user profile tables that use user_id as PK."""

    def __init__(self, model: Type[P]) -> None:
        self.model = model

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> P | None:
        try:
            result = await db.execute(
                select(self.model).where(self.model.user_id == user_id)  # type: ignore[attr-defined]
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to fetch {self.model.__name__}: {e}") from e

    async def upsert(self, db: AsyncSession, user_id: int, data: dict) -> P:
        try:
            result = await db.execute(
                select(self.model).where(self.model.user_id == user_id)  # type: ignore[attr-defined]
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                profile = self.model(user_id=user_id, **data)  # type: ignore[call-arg]
                db.add(profile)
            else:
                for key, value in data.items():
                    setattr(profile, key, value)
            await db.flush()
            await db.refresh(profile)
            return profile
        except Exception as e:
            raise DatabaseError(f"Failed to upsert {self.model.__name__}: {e}") from e


class InvestorProfileRepository(ProfileRepository[InvestorProfile]):
    def __init__(self) -> None:
        super().__init__(InvestorProfile)


class ResearcherProfileRepository(ProfileRepository[ResearcherProfile]):
    def __init__(self) -> None:
        super().__init__(ResearcherProfile)


class SponsorProfileRepository(ProfileRepository[SponsorProfile]):
    def __init__(self) -> None:
        super().__init__(SponsorProfile)


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        try:
            result = await db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to fetch user by e-mail {email}: {e}") from e

    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        stmt = select(exists().where(User.email == email))
        result = await db.execute(stmt)
        return bool(result.scalar())

    async def get_by_token_hash(
        self, db: AsyncSession, token_hash: str, token_type: TokenType
    ) -> User | None:
        try:
            result = await db.execute(
                select(User).where(
                    User.token_hash == token_hash,
                    User.token_type == token_type,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover
            raise DatabaseError(f"Failed to fetch user by token hash: {e}") from e


class UserCategoryRepository:
    async def get_by_user_id(
        self, db: AsyncSession, user_id: int
    ) -> list[UserCategory]:
        try:
            result = await db.execute(
                select(UserCategory).where(UserCategory.user_id == user_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to fetch user categories: {e}") from e

    async def add_category(
        self, db: AsyncSession, user_id: int, category_id: int
    ) -> UserCategory:
        try:
            entry = UserCategory(user_id=user_id, category_id=category_id)
            db.add(entry)
            await db.flush()
            return entry
        except Exception as e:
            raise DatabaseError(f"Failed to add user category: {e}") from e

    async def remove_category(
        self, db: AsyncSession, user_id: int, category_id: int
    ) -> None:
        try:
            await db.execute(
                delete(UserCategory).where(
                    UserCategory.user_id == user_id,
                    UserCategory.category_id == category_id,
                )
            )
            await db.flush()
        except Exception as e:
            raise DatabaseError(f"Failed to remove user category: {e}") from e

    async def set_categories(
        self, db: AsyncSession, user_id: int, category_ids: list[int]
    ) -> list[UserCategory]:
        try:
            await sync_association(db, UserCategory.__table__, "user_id", user_id, "category_id", set(category_ids))
            await db.flush()
            result = await db.execute(select(UserCategory).where(UserCategory.user_id == user_id))
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to set user categories: {e}") from e
