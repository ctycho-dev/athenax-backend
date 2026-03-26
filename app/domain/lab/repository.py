from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.lab.model import Lab, Category
from app.domain.lab.schema import LabCreateSchema, LabOutSchema
from app.exceptions.exceptions import DatabaseError, NotFoundError


class LabRepository(BaseRepository[Lab]):
    def __init__(self) -> None:
        super().__init__(Lab)

    async def create_lab(
        self,
        db: AsyncSession,
        entity: dict | LabCreateSchema,
        current_user_id: int | None = None,
    ) -> LabOutSchema:
        try:
            data = entity.model_dump() if isinstance(entity, BaseModel) else dict(entity)
            category_ids = data.pop("category_ids", [])
            new_category_names = data.pop("new_categories", [])

            categories = await self._get_categories_by_ids(db, category_ids)
            if new_category_names:
                categories += await self._get_or_create_categories_by_name(db, new_category_names)

            db_obj = Lab(**data)
            db_obj.categories = categories

            now = datetime.now(timezone.utc)
            db_obj.created_at = now
            db_obj.updated_at = now

            if current_user_id and hasattr(db_obj, "created_by"):
                db_obj.created_by = current_user_id
            if current_user_id and hasattr(db_obj, "updated_by"):
                db_obj.updated_by = current_user_id

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return LabOutSchema.model_validate(db_obj)
        except NotFoundError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to create entity: {str(e)}") from e

    async def update_lab(
        self,
        db: AsyncSession,
        _id: int,
        update_data: dict | BaseModel,
        current_user_id: int | None = None,
    ) -> LabOutSchema:
        try:
            result = await db.execute(select(Lab).where(Lab.id == _id))
            instance = result.scalar_one_or_none()
            if not instance:
                raise NotFoundError(f"Entity with ID {_id} not found")

            payload = update_data.model_dump(exclude_unset=True) if isinstance(update_data, BaseModel) else dict(update_data)
            category_ids = payload.pop("category_ids", None)

            protected_fields = {"id", "created_at", "created_by"}
            for key, value in payload.items():
                if key not in protected_fields:
                    setattr(instance, key, value)

            if category_ids is not None:
                instance.categories = await self._get_categories_by_ids(db, category_ids)

            if current_user_id and hasattr(instance, "updated_by"):
                instance.updated_by = current_user_id

            await db.commit()
            await db.refresh(instance)
            return LabOutSchema.model_validate(instance)
        except NotFoundError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to update entity: {str(e)}") from e

    async def _get_or_create_categories_by_name(
        self,
        db: AsyncSession,
        names: list[str],
    ) -> list[Category]:
        unique_names = list(dict.fromkeys(names))
        result = await db.execute(select(Category).where(Category.name.in_(unique_names)))
        existing = {c.name: c for c in result.scalars().all()}

        for name in unique_names:
            if name not in existing:
                new_cat = Category(name=name)
                db.add(new_cat)
                existing[name] = new_cat

        await db.flush()
        return list(existing.values())

    async def _get_categories_by_ids(
        self,
        db: AsyncSession,
        category_ids: list[int],
    ) -> list[Category]:
        if not category_ids:
            return []

        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(select(Category).where(Category.id.in_(unique_ids)))
        categories = list(result.scalars().all())

        found_ids = {category.id for category in categories}
        missing_ids = [category_id for category_id in unique_ids if category_id not in found_ids]
        if missing_ids:
            raise NotFoundError(f"Category IDs not found: {missing_ids}")

        return categories
