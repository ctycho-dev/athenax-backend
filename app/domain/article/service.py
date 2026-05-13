from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_association
from app.common.permissions import is_admin
from app.domain.article.model import ArticleTag
from app.domain.article.repository import ArticleRepository
from app.domain.article.schema import ArticleCreateSchema, ArticleOutSchema, ArticleUpdateSchema
from app.domain.tag.repository import TagRepository
from app.domain.user.repository import UserRepository
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ArticleStatus
from app.exceptions.exceptions import NotFoundError
from app.utils.slug import generate_slug


class ArticleService:
    def __init__(
        self,
        repo: ArticleRepository,
        tag_repo: TagRepository,
        user_repo: UserRepository,
    ):
        self.repo = repo
        self.tag_repo = tag_repo
        self.user_repo = user_repo

    async def create(
        self,
        db: AsyncSession,
        data: ArticleCreateSchema,
        current_user: UserOutSchema,
    ) -> ArticleOutSchema:
        payload = data.model_dump()
        tag_names = payload.pop("tags", [])

        payload["slug"] = generate_slug(data.title)
        payload = self._apply_published_at(payload)

        article = await self.repo.create(db, payload, current_user_id=current_user.id)
        await self._sync_tags(db, article.id, tag_names)

        await db.commit()
        await db.refresh(article)
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
    ) -> list[ArticleOutSchema]:
        # Non-admins may only see published articles
        if current_user is None or not is_admin(current_user):
            status = ArticleStatus.PUBLISHED

        articles = await self.repo.get_all_filtered(db, status=status, article_type=article_type, tag=tag, limit=limit, offset=offset)
        if not articles:
            return []

        article_ids = [a.id for a in articles]
        creator_ids = list({a.created_by_id for a in articles if a.created_by_id})

        tags_map, users_map = await _gather(
            self.repo.get_tags_for_articles(db, article_ids),
            self.user_repo.get_by_ids(db, creator_ids),
        )

        results = []
        for article in articles:
            out = ArticleOutSchema.model_validate(article, from_attributes=True)
            out.tags = [t.name for t in tags_map[article.id]]
            out.creator_name = users_map[article.created_by_id].name if article.created_by_id in users_map else None
            results.append(out)
        return results

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
        payload = data.model_dump(exclude_unset=True)
        tag_names = payload.pop("tags", None)

        if "title" in payload:
            payload["slug"] = generate_slug(payload["title"])

        if "status" in payload:
            payload = self._apply_published_at(payload, current_published_at=article.published_at)

        article = await self.repo.update(db, article_id, payload, current_user_id=current_user.id)

        if tag_names is not None:
            await self._sync_tags(db, article_id, tag_names)

        await db.commit()
        await db.refresh(article)
        return await self._to_schema(db, article)

    async def delete_by_id(self, db: AsyncSession, article_id: int) -> None:
        await self.repo.get_by_id(db, article_id)
        await self.repo.delete_by_id(db, article_id)
        await db.commit()

    # -------------------------
    # Helpers
    # -------------------------

    async def _sync_tags(self, db: AsyncSession, article_id: int, tag_names: list[str]) -> None:
        names = list({n.lower().strip() for n in tag_names if n.strip()})
        existing = await self.tag_repo.get_by_names(db, names)
        existing_names = {t.name for t in existing}
        new_tags = [
            await self.tag_repo.create(db, {"name": name})
            for name in names
            if name not in existing_names
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
        elif new_status is not None:
            payload["published_at"] = None
        return payload

    async def _to_schema(self, db: AsyncSession, article) -> ArticleOutSchema:
        tags, users_map = await _gather(
            self.repo.get_tags_for_article(db, article.id),
            self.user_repo.get_by_ids(db, [article.created_by_id] if article.created_by_id else []),
        )
        out = ArticleOutSchema.model_validate(article, from_attributes=True)
        out.tags = [t.name for t in tags]
        out.creator_name = users_map[article.created_by_id].name if article.created_by_id in users_map else None
        return out


async def _gather(*coros):
    import asyncio
    return await asyncio.gather(*coros)
