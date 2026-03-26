from typing import Type, TypeVar, Generic, Optional, Any, Union, runtime_checkable, Protocol
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.exceptions.exceptions import NotFoundError, DatabaseError

@runtime_checkable
class AudiProtocol(Protocol):
    id: Any
    created_by_id: Optional[int]
    updated_by_id: Optional[int]
    deleted_at: Any

T = TypeVar("T", bound=AudiProtocol)


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def get_by_id(self, session: AsyncSession, _id: int) -> T:
        try:
            result = await session.execute(select(self.model).where(self.model.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"{self.model.__name__} with ID {_id} not found")
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve {self.model.__name__}: {e}") from e

    async def get_all(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        try:
            result = await session.execute(select(self.model).limit(limit).offset(offset))
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve {self.model.__name__} list: {e}") from e

    async def create(
        self,
        session: AsyncSession,
        data: Union[dict[str, Any], BaseModel],
        current_user_id: int | None = None,
    ) -> T:
        try:
            payload = data.model_dump() if isinstance(data, BaseModel) else data
            instance = self.model(**payload)
            if current_user_id and hasattr(instance, "created_by_id"):
                instance.created_by_id = current_user_id
            if current_user_id and hasattr(instance, "updated_by_id"):
                instance.updated_by_id = current_user_id
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            return instance
        except Exception as e:
            raise DatabaseError(f"Failed to create {self.model.__name__}: {e}") from e

    async def update(
        self,
        session: AsyncSession,
        _id: int,
        data: Union[dict[str, Any], BaseModel],
        current_user_id: int | None = None,
    ) -> T:
        try:
            result = await session.execute(select(self.model).where(self.model.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"{self.model.__name__} with ID {_id} not found")

            payload = data.model_dump(exclude_unset=True) if isinstance(data, BaseModel) else data

            protected_fields = {"id", "created_at", "created_by_id"}
            for key, value in payload.items():
                if key not in protected_fields:
                    setattr(instance, key, value)

            if current_user_id and hasattr(instance, "updated_by_id"):
                instance.updated_by_id = current_user_id

            await session.flush()
            await session.refresh(instance)
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update {self.model.__name__}: {e}") from e
    
    async def update_instance(
        self,
        session: AsyncSession,
        instance: T,
        data: Union[dict[str, Any], BaseModel],
        current_user_id: int | None = None,
    ) -> T:
        try:
            payload = data.model_dump(exclude_unset=True) if isinstance(data, BaseModel) else data

            protected_fields = {"id", "created_at", "created_by_id"}
            for key, value in payload.items():
                if key not in protected_fields:
                    setattr(instance, key, value)

            if current_user_id and hasattr(instance, "updated_by_id"):
                instance.updated_by_id = current_user_id

            await session.flush()
            return instance
        except Exception as e:
            raise DatabaseError(f"Failed to update {self.model.__name__}: {e}") from e

    async def delete_by_id(self, session: AsyncSession, _id: int) -> None:
        try:
            result = await session.execute(select(self.model).where(self.model.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"{self.model.__name__} with ID {_id} not found")
            await session.delete(instance)
            await session.flush()
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delete {self.model.__name__}: {e}") from e

    async def soft_delete(self, session: AsyncSession, _id: int) -> None:
        from datetime import datetime, timezone
        try:
            result = await session.execute(
                select(self.model).where(
                    and_(self.model.id == _id, self.model.deleted_at.is_(None))
                )
            )
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"{self.model.__name__} with ID {_id} not found")
            if hasattr(instance, "deleted_at"):
                instance.deleted_at = datetime.now(timezone.utc)
            await session.flush()
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to soft delete {self.model.__name__}: {e}") from e