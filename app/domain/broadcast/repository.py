from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.common.base_repository import BaseRepository
from app.domain.broadcast.model import Broadcast, BroadcastTag
from app.domain.tag.model import Tag
from app.enums.enums import BroadcastStatus, BroadcastType
from app.exceptions.exceptions import NotFoundError


class BroadcastRepository(BaseRepository[Broadcast]):
    def __init__(self) -> None:
        super().__init__(Broadcast)

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Broadcast:
        result = await db.execute(
            select(Broadcast).where(Broadcast.slug == slug, Broadcast.deleted_at.is_(None))
        )
        broadcast = result.scalar_one_or_none()
        if broadcast is None:
            raise NotFoundError(f"Broadcast with slug '{slug}' not found")
        return broadcast

    async def get_all_filtered(
        self,
        db: AsyncSession,
        status: BroadcastStatus | None,
        broadcast_type: BroadcastType | None,
        tag: str | None,
        limit: int,
        offset: int,
    ) -> list[Broadcast]:
        # Prune the large `description` body — the list path serializes summaries only.
        q = select(Broadcast).options(
            load_only(
                Broadcast.title, Broadcast.slug, Broadcast.broadcast_type,
                Broadcast.status, Broadcast.origin_date, Broadcast.published_at,
                Broadcast.created_at, Broadcast.updated_at,
            )
        ).where(Broadcast.deleted_at.is_(None))
        if status is not None:
            q = q.where(Broadcast.status == status)
        if broadcast_type is not None:
            q = q.where(Broadcast.broadcast_type == broadcast_type)
        if tag is not None:
            q = q.where(
                exists(
                    select(BroadcastTag.broadcast_id)
                    .join(Tag, Tag.id == BroadcastTag.tag_id)
                    .where(
                        BroadcastTag.broadcast_id == Broadcast.id,
                        func.lower(Tag.name) == tag.lower().strip(),
                    )
                )
            )
        q = q.order_by(Broadcast.origin_date.desc().nulls_last(), Broadcast.id.desc()).limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_tags_for_broadcasts(
        self, db: AsyncSession, broadcast_ids: list[int]
    ) -> dict[int, list[Tag]]:
        result = await db.execute(
            select(BroadcastTag.broadcast_id, Tag)
            .join(Tag, Tag.id == BroadcastTag.tag_id)
            .where(BroadcastTag.broadcast_id.in_(broadcast_ids))
        )
        groups: dict[int, list[Tag]] = {bid: [] for bid in broadcast_ids}
        for row in result:
            groups[row.broadcast_id].append(row.Tag)
        return groups

    async def get_tags_for_broadcast(
        self, db: AsyncSession, broadcast_id: int
    ) -> list[Tag]:
        return (await self.get_tags_for_broadcasts(db, [broadcast_id]))[broadcast_id]
