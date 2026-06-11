import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_association
from app.common.permissions import is_admin
from app.domain.broadcast.model import BroadcastTag
from app.domain.broadcast.repository import BroadcastRepository
from app.domain.broadcast.schema import (
    BroadcastCreateSchema,
    BroadcastOutSchema,
    BroadcastSummarySchema,
    BroadcastUpdateSchema,
)
from app.domain.tag.repository import TagRepository
from app.domain.user.repository import UserRepository
from app.domain.user.schema import UserOutSchema
from app.enums.enums import BroadcastStatus
from app.common.cache_keys import BROADCAST_LIST_PREFIX
from app.exceptions.exceptions import NotFoundError
from app.infrastructure.redis.client import RedisClient
from app.utils.slug import slugify


class BroadcastService:
    def __init__(
        self,
        repo: BroadcastRepository,
        tag_repo: TagRepository,
        user_repo: UserRepository,
        redis: RedisClient | None = None,
    ):
        self.repo = repo
        self.tag_repo = tag_repo
        self.user_repo = user_repo
        self.redis = redis

    async def _invalidate_list_cache(self) -> None:
        if self.redis:
            await self.redis.delete_by_pattern(f"{BROADCAST_LIST_PREFIX}:*")

    async def create(
        self,
        db: AsyncSession,
        data: BroadcastCreateSchema,
        current_user: UserOutSchema,
    ) -> BroadcastOutSchema:
        payload = data.model_dump()
        tag_names = payload.pop("tags", [])

        payload["slug"] = slugify(data.title)
        payload = self._apply_published_at(payload)

        broadcast = await self.repo.create(db, payload, current_user_id=current_user.id)
        await self._sync_tags(db, broadcast.id, tag_names)

        await db.commit()
        await db.refresh(broadcast)
        await self._invalidate_list_cache()
        return await self._to_schema(db, broadcast)

    async def list_broadcasts(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        status: BroadcastStatus | None,
        broadcast_type,
        tag: str | None,
        current_user: UserOutSchema | None,
    ) -> list[BroadcastSummarySchema]:
        if current_user is None or not is_admin(current_user):
            status = BroadcastStatus.PUBLISHED

        broadcasts = await self.repo.get_all_filtered(
            db, status=status, broadcast_type=broadcast_type, tag=tag, limit=limit, offset=offset
        )
        if not broadcasts:
            return []

        broadcast_ids = [b.id for b in broadcasts]
        tags_map = await self.repo.get_tags_for_broadcasts(db, broadcast_ids)

        results = []
        for broadcast in broadcasts:
            # List path omits the large `description` body — repo prunes it from the SELECT too.
            out = BroadcastSummarySchema.model_validate(broadcast, from_attributes=True)
            out.tags = [t.name for t in tags_map[broadcast.id]]
            results.append(out)
        return results

    async def get_by_id(
        self,
        db: AsyncSession,
        broadcast_id: int,
        current_user: UserOutSchema | None,
    ) -> BroadcastOutSchema:
        broadcast = await self.repo.get_by_id(db, broadcast_id)
        self._assert_visible(broadcast, current_user)
        return await self._to_schema(db, broadcast)

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        current_user: UserOutSchema | None,
    ) -> BroadcastOutSchema:
        broadcast = await self.repo.get_by_slug(db, slug)
        self._assert_visible(broadcast, current_user)
        return await self._to_schema(db, broadcast)

    async def update(
        self,
        db: AsyncSession,
        broadcast_id: int,
        data: BroadcastUpdateSchema,
        current_user: UserOutSchema,
    ) -> BroadcastOutSchema:
        broadcast = await self.repo.get_by_id(db, broadcast_id)
        payload = data.model_dump(exclude_unset=True)
        tag_names = payload.pop("tags", None)

        if "slug" in payload:
            payload["slug"] = slugify(payload["slug"])
        elif "title" in payload:
            payload["slug"] = slugify(payload["title"])

        if "status" in payload:
            payload = self._apply_published_at(payload, current_published_at=broadcast.published_at)

        broadcast = await self.repo.update(db, broadcast_id, payload, current_user_id=current_user.id)

        if tag_names is not None:
            await self._sync_tags(db, broadcast_id, tag_names)

        await db.commit()
        await db.refresh(broadcast)
        await self._invalidate_list_cache()
        return await self._to_schema(db, broadcast)

    async def delete_by_id(self, db: AsyncSession, broadcast_id: int, current_user: UserOutSchema) -> None:
        await self.repo.soft_delete(db, broadcast_id, deleted_by_id=current_user.id)
        await db.commit()
        await self._invalidate_list_cache()

    # -------------------------
    # Helpers
    # -------------------------

    async def _sync_tags(self, db: AsyncSession, broadcast_id: int, tag_names: list[str]) -> None:
        seen: dict[str, str] = {}
        for n in tag_names:
            stripped = n.strip()
            if stripped and stripped.lower() not in seen:
                seen[stripped.lower()] = stripped
        names = list(seen.values())
        existing = await self.tag_repo.get_by_names(db, names)
        existing_lower = {t.name.lower() for t in existing}
        new_tags = [
            await self.tag_repo.create(db, {"name": name})
            for name in names
            if name.lower() not in existing_lower
        ]
        all_ids = {t.id for t in existing} | {t.id for t in new_tags}
        await sync_association(db, BroadcastTag.__table__, "broadcast_id", broadcast_id, "tag_id", all_ids)

    def _assert_visible(self, broadcast, current_user: UserOutSchema | None) -> None:
        if broadcast.status != BroadcastStatus.PUBLISHED:
            if current_user is None or not is_admin(current_user):
                raise NotFoundError(f"Broadcast with id '{broadcast.id}' not found")

    def _apply_published_at(
        self,
        payload: dict,
        current_published_at: datetime | None = None,
    ) -> dict:
        new_status = payload.get("status")
        if new_status == BroadcastStatus.PUBLISHED:
            if payload.get("published_at") is None and current_published_at is None:
                payload["published_at"] = datetime.now(timezone.utc)
        elif new_status is not None:
            payload["published_at"] = None
        return payload

    async def _to_schema(self, db: AsyncSession, broadcast) -> BroadcastOutSchema:
        tags, users_map = await asyncio.gather(
            self.repo.get_tags_for_broadcast(db, broadcast.id),
            self.user_repo.get_by_ids(db, [broadcast.created_by_id] if broadcast.created_by_id else []),
        )
        out = BroadcastOutSchema.model_validate(broadcast, from_attributes=True)
        out.tags = [t.name for t in tags]
        out.creator_name = users_map[broadcast.created_by_id].name if broadcast.created_by_id in users_map else None
        return out
