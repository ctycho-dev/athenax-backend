from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.common.db_utils import sync_association
from app.domain.category.model import Category
from app.domain.lab.model import Lab, LabCategory
from app.domain.lab.schema import LabCreateSchema
from app.exceptions.exceptions import DatabaseError, NotFoundError


class LabRepository(BaseRepository[Lab]):
    def __init__(self) -> None:
        super().__init__(Lab)

    async def create_lab(
        self,
        db: AsyncSession,
        entity: dict | LabCreateSchema,
        current_user_id: int | None = None,
    ) -> Lab:
        try:
            data = entity.model_dump() if isinstance(entity, BaseModel) else dict(entity)
            category_ids = data.pop("category_ids", [])
            new_category_names = data.pop("new_categories", [])

            resolved_ids = list(category_ids)
            if category_ids:
                await self._assert_categories_exist(db, category_ids)
            if new_category_names:
                new_ids = await self._get_or_create_categories_by_name(db, new_category_names)
                resolved_ids += new_ids

            db_obj = Lab(**data)
            if current_user_id and hasattr(db_obj, "created_by_id"):
                db_obj.created_by_id = current_user_id
            if current_user_id and hasattr(db_obj, "updated_by_id"):
                db_obj.updated_by_id = current_user_id

            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)

            await sync_association(db, LabCategory.__table__, "lab_id", db_obj.id, "category_id", set(resolved_ids))
            await db.flush()
            return db_obj
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
    ) -> Lab:
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

            if current_user_id and hasattr(instance, "updated_by_id"):
                instance.updated_by_id = current_user_id

            if category_ids is not None:
                await self._assert_categories_exist(db, category_ids)
                await sync_association(db, LabCategory.__table__, "lab_id", _id, "category_id", set(category_ids))

            await db.flush()
            return instance
        except NotFoundError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseError(f"Failed to update entity: {str(e)}") from e

    async def get_categories_for_lab(self, db: AsyncSession, lab_id: int) -> list[Category]:
        result = await db.execute(
            select(Category)
            .join(LabCategory.__table__, Category.id == LabCategory.__table__.c.category_id)
            .where(LabCategory.__table__.c.lab_id == lab_id)
        )
        return list(result.scalars().all())

    async def _assert_categories_exist(self, db: AsyncSession, category_ids: list[int]) -> None:
        if not category_ids:
            return
        unique_ids = list(dict.fromkeys(category_ids))
        result = await db.execute(select(Category.id).where(Category.id.in_(unique_ids)))
        found_ids = {row[0] for row in result.all()}
        missing = [cid for cid in unique_ids if cid not in found_ids]
        if missing:
            raise NotFoundError(f"Category IDs not found: {missing}")

    async def _get_or_create_categories_by_name(
        self,
        db: AsyncSession,
        names: list[str],
    ) -> list[int]:
        unique_names = list(dict.fromkeys(names))
        result = await db.execute(select(Category).where(Category.name.in_(unique_names)))
        existing = {c.name: c for c in result.scalars().all()}

        for name in unique_names:
            if name not in existing:
                new_cat = Category(name=name)
                db.add(new_cat)
                existing[name] = new_cat

        await db.flush()
        return [existing[name].id for name in unique_names]
