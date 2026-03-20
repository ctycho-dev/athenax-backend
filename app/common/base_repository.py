# app/common/base_repository.py
from typing import Type, TypeVar, Generic, Optional, Dict, Any, Union
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app.exceptions.exceptions import NotFoundError, DatabaseError


T = TypeVar("T")  # SQLAlchemy model
S = TypeVar("S", bound=BaseModel)  # Output schema
C = TypeVar("C", bound=BaseModel)  # Create schema


class BaseRepository(Generic[T, S, C]):
    def __init__(
        self,
        model: Type[T],
        default_schema: Type[S],
        create_schema: Type[C],
    ):
        self.model = model
        self.default_schema = default_schema
        self.create_schema = create_schema

    async def get_by_id(self, db: AsyncSession, _id: int) -> Optional[S]:
        try:
            result = await db.execute(select(self.model).where(self.model.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"Entity with ID {_id} not found")
            return self.default_schema.model_validate(instance)
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve entity: {str(e)}") from e

    async def get_all(self, db: AsyncSession, schema: Optional[Type[S]] = None) -> list[S]:
        try:
            result = await db.execute(select(self.model))
            instances = result.scalars().all()
            schema_cls = schema or self.default_schema
            return [schema_cls.model_validate(instance) for instance in instances]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve all entities: {str(e)}") from e

    async def create(
        self,
        db: AsyncSession,
        entity: Union[Dict[str, Any], C],
        schema: Optional[Type[S]] = None,
        current_user_id: int | None = None,
    ) -> S:
        try:
            if isinstance(entity, BaseModel):
                data = entity.model_dump()
            else:
                data = entity

            db_obj = self.model(**data)
            # Set audit fields if they exist
            now = datetime.now(timezone.utc)
            if hasattr(db_obj, 'created_at'):
                db_obj.created_at = now
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = now
            if current_user_id and hasattr(db_obj, 'created_by'):
                db_obj.created_by = current_user_id
            if current_user_id and hasattr(db_obj, 'updated_by'):
                db_obj.updated_by = current_user_id

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)

            schema_cls = schema or self.default_schema
            return schema_cls.model_validate(db_obj)
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to create entity: {str(e)}") from e

    async def update(
        self,
        db: AsyncSession,
        _id: int,
        update_data: Union[Dict[str, Any], BaseModel],
        schema: Optional[Type[S]] = None,
        current_user_id: int | None = None,
    ) -> S:
        try:
            # if hasattr(self.model, 'deleted_at'):
            #     query = select(self.model).where(
            #         and_(self.model.id == _id, self.model.deleted_at.is_(None))
            #     )
            # else:
            query = select(self.model).where(self.model.id == _id)
                
            result = await db.execute(query)
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"Entity with ID {_id} not found")

            if isinstance(update_data, BaseModel):
                update_data = update_data.model_dump(exclude_unset=True)

            # Protected fields that should never be updated
            protected_fields = {"id", "created_at", "created_by"}
            # protected_fields = {"id", "created_at", "created_by", "deleted_at", "deleted_by"}
            
            # Update only allowed fields
            for key, value in update_data.items():
                if key not in protected_fields:
                    setattr(instance, key, value)

            # Always update audit fields if they exist
            if current_user_id and hasattr(instance, "updated_by"):
                setattr(instance, "updated_by", current_user_id)

            await db.commit()
            await db.refresh(instance)

            schema_cls = schema or self.default_schema
            return schema_cls.model_validate(instance)
        except NotFoundError:
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to update entity: {str(e)}") from e

    async def soft_delete(
        self,
        db: AsyncSession,
        _id: int,
        current_user_id: Optional[str] = None,
    ) -> None:
        """Soft delete an entity by setting deleted_at and deleted_by."""
        try:
            result = await db.execute(
                select(self.model).where(
                    and_(self.model.id == _id, self.model.deleted_at.is_(None))
                )
            )
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"Entity with ID {_id} not found")

            # Set soft delete fields
            if hasattr(instance, "deleted_at"):
                instance.deleted_at = datetime.now(timezone.utc)
            if current_user_id and hasattr(instance, "deleted_by"):
                instance.deleted_by = current_user_id

            await db.commit()
        except NotFoundError:
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to soft delete entity: {str(e)}") from e

    async def delete_by_id(self, db: AsyncSession, _id: int) -> None:
        """Hard delete an entity (permanently removes from database)."""
        try:
            result = await db.execute(select(self.model).where(self.model.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"Entity with ID {_id} not found")

            await db.delete(instance)
            await db.commit()
        except NotFoundError:
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete entity: {str(e)}") from e
