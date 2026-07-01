import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.cache_keys import ARTICLE_DETAIL_PREFIX, ARTICLE_LIST_PREFIX, BROADCAST_DETAIL_PREFIX
from app.common.db_utils import sync_association
from app.common.permissions import is_admin
from app.common.schema import PaginatedSchema
from app.domain.article.model import ArticleTag
from app.domain.article.repository import ArticleRepository
from app.domain.article.schema import ArticleCreateSchema, ArticleOutSchema, ArticleSummarySchema, ArticleUpdateSchema
from app.domain.broadcast.repository import BroadcastRepository
from app.domain.tag.repository import TagRepository
from app.domain.user.repository import UserRepository
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ArticleStatus
from app.exceptions.exceptions import ConflictError, NotFoundError
from app.infrastructure.redis.client import RedisClient
from app.utils.slug import slugify, with_random_suffix


class ArticleService:
    def __init__(
        self,
        repo: ArticleRepository,
        tag_repo: TagRepository,
        user_repo: UserRepository,
        broadcast_repo: BroadcastRepository,
        redis: RedisClient | None = None,
    ):
        self.repo = repo
        self.tag_repo = tag_repo
        self.user_repo = user_repo
        self.broadcast_repo = broadcast_repo
        self.redis = redis

    async def _invalidate_list_cache(self) -> None:
        if self.redis:
            await self.redis.delete_by_pattern(f"{ARTICLE_LIST_PREFIX}:*")

    async def _invalidate_detail_cache(self, slug: str) -> None:
        if self.redis:
            await self.redis.delete(f"{ARTICLE_DETAIL_PREFIX}:{slug}")

    async def _invalidate_broadcast_detail_cache(self, db: AsyncSession, broadcast_id: int | None) -> None:
        if not self.redis or not broadcast_id:
            return
        try:
            broadcast = await self.broadcast_repo.get_by_id(db, broadcast_id)
            await self.redis.delete(f"{BROADCAST_DETAIL_PREFIX}:{broadcast.slug}")
        except NotFoundError:
            pass

    async def create(
        self,
        db: AsyncSession,
        data: ArticleCreateSchema,
        current_user: UserOutSchema,
    ) -> ArticleOutSchema:
        payload = data.model_dump()
        tag_names = payload.pop("tags", [])

        if data.broadcast_id:
            await self.broadcast_repo.get_by_id(db, data.broadcast_id)

        base = slugify(data.title)
        payload["slug"] = base
        payload = self._apply_published_at(payload)

        try:
            async with db.begin_nested():
                article = await self.repo.create(db, payload, current_user_id=current_user.id)
        except ConflictError:
            payload["slug"] = with_random_suffix(base)
            article = await self.repo.create(db, payload, current_user_id=current_user.id)
        await self._sync_tags(db, article.id, tag_names)

        await db.commit()
        await db.refresh(article)
        await asyncio.gather(
            self._invalidate_list_cache(),
            self._invalidate_broadcast_detail_cache(db, article.broadcast_id),
        )
        return await self._to_schema(db, article)

    async def list_articles(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        status: ArticleStatus | None,
        article_type,
        tag: str | None,
        current_user: UserOutSchema | None,
    ) -> PaginatedSchema[ArticleSummarySchema]:
        # Non-admins may only see published articles
        if current_user is None or not is_admin(current_user):
            status = ArticleStatus.PUBLISHED

        # List path omits the large `content` body — repo prunes it from the SELECT too.
        total = await self.repo.count_filtered(db, status=status, article_type=article_type, tag=tag)
        articles = await self.repo.get_all_filtered(db, status=status, article_type=article_type, tag=tag, limit=limit, offset=offset)
        if not articles:
            return PaginatedSchema(items=[], total=total)

        article_ids = [a.id for a in articles]
        tags_map = await self.repo.get_tags_for_articles(db, article_ids)

        results = []
        for article in articles:
            out = ArticleSummarySchema.model_validate(article, from_attributes=True)
            out.tags = [t.name for t in tags_map[article.id]]
            results.append(out)
        return PaginatedSchema(items=results, total=total)

    async def get_by_id(
        self,
        db: AsyncSession,
        article_id: int,
        current_user: UserOutSchema | None,
    ) -> ArticleOutSchema:
        article = await self.repo.get_by_id(db, article_id)
        self._assert_visible(article, current_user)
        return await self._to_schema(db, article)

    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        current_user: UserOutSchema | None,
    ) -> ArticleOutSchema:
        article = await self.repo.get_by_slug(db, slug)
        self._assert_visible(article, current_user)
        return await self._to_schema(db, article)

    async def update(
        self,
        db: AsyncSession,
        article_id: int,
        data: ArticleUpdateSchema,
        current_user: UserOutSchema,
    ) -> ArticleOutSchema:
        article = await self.repo.get_by_id(db, article_id)
        old_slug = article.slug
        old_broadcast_id = article.broadcast_id
        payload = data.model_dump(exclude_unset=True)
        tag_names = payload.pop("tags", None)

        if payload.get("broadcast_id"):
            await self.broadcast_repo.get_by_id(db, payload["broadcast_id"])

        if "slug" in payload:
            payload["slug"] = slugify(payload["slug"])
        elif "title" in payload:
            payload["slug"] = slugify(payload["title"])

        if "status" in payload:
            payload = self._apply_published_at(payload, current_published_at=article.published_at)

        try:
            async with db.begin_nested():
                article = await self.repo.update(db, article_id, payload, current_user_id=current_user.id)
        except ConflictError:
            slug_source = payload.get("slug") or payload.get("title", "")
            payload["slug"] = with_random_suffix(slugify(slug_source))
            article = await self.repo.update(db, article_id, payload, current_user_id=current_user.id)

        if tag_names is not None:
            await self._sync_tags(db, article_id, tag_names)

        await db.commit()
        await db.refresh(article)

        invalidations = [self._invalidate_list_cache(), self._invalidate_detail_cache(article.slug)]
        if old_slug != article.slug:
            invalidations.append(self._invalidate_detail_cache(old_slug))
        # Invalidate broadcast cache for both old and new broadcast_id when the link changes
        if "broadcast_id" in payload:
            invalidations.append(self._invalidate_broadcast_detail_cache(db, old_broadcast_id))
            invalidations.append(self._invalidate_broadcast_detail_cache(db, article.broadcast_id))
        await asyncio.gather(*invalidations)

        return await self._to_schema(db, article)

    async def delete_by_id(self, db: AsyncSession, article_id: int, current_user: UserOutSchema) -> None:
        article = await self.repo.get_by_id(db, article_id)
        await self.repo.soft_delete(db, article_id, deleted_by_id=current_user.id)
        await db.commit()
        await asyncio.gather(
            self._invalidate_list_cache(),
            self._invalidate_detail_cache(article.slug),
            self._invalidate_broadcast_detail_cache(db, article.broadcast_id),
        )

    # -------------------------
    # Helpers
    # -------------------------

    async def _sync_tags(self, db: AsyncSession, article_id: int, tag_names: list[str]) -> None:
        # Dedup by lowercase key, preserving original casing of the first occurrence
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
        await sync_association(db, ArticleTag.__table__, "article_id", article_id, "tag_id", all_ids)

    def _assert_visible(self, article, current_user: UserOutSchema | None) -> None:
        if article.status != ArticleStatus.PUBLISHED:
            if current_user is None or not is_admin(current_user):
                raise NotFoundError(f"Article with id '{article.id}' not found")

    def _apply_published_at(
        self,
        payload: dict,
        current_published_at: datetime | None = None,
    ) -> dict:
        new_status = payload.get("status")
        if new_status == ArticleStatus.PUBLISHED:
            if payload.get("published_at") is None and current_published_at is None:
                payload["published_at"] = datetime.now(timezone.utc)
        elif new_status is not None and payload.get("published_at") is None:
            # Clear the date when unpublishing, but keep an explicitly chosen one.
            payload["published_at"] = None
        return payload

    async def _to_schema(self, db: AsyncSession, article) -> ArticleOutSchema:
        tags, users_map = await asyncio.gather(
            self.repo.get_tags_for_article(db, article.id),
            self.user_repo.get_by_ids(db, [article.created_by_id] if article.created_by_id else []),
        )
        out = ArticleOutSchema.model_validate(article, from_attributes=True)
        out.tags = [t.name for t in tags]
        out.creator_name = users_map[article.created_by_id].name if article.created_by_id in users_map else None
        return out
