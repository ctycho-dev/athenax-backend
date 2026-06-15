from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.common.base_repository import BaseRepository
from app.domain.article.model import Article, ArticleTag
from app.domain.tag.model import Tag
from app.enums.enums import ArticleStatus, ArticleType
from app.exceptions.exceptions import NotFoundError


class ArticleRepository(BaseRepository[Article]):
    def __init__(self) -> None:
        super().__init__(Article)

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Article:
        result = await db.execute(
            select(Article).where(Article.slug == slug, Article.deleted_at.is_(None))
        )
        article = result.scalar_one_or_none()
        if article is None:
            raise NotFoundError(f"Article with slug '{slug}' not found")
        return article

    async def get_all_filtered(
        self,
        db: AsyncSession,
        status: ArticleStatus | None,
        article_type: ArticleType | None,
        tag: str | None,
        limit: int,
        offset: int,
    ) -> list[Article]:
        # Prune the large `content` body — the list path serializes summaries only.
        q = select(Article).options(
            load_only(
                Article.title,
                Article.slug,
                Article.article_type,
                Article.status,
                Article.published_at,
                Article.created_at,
            )
        ).where(Article.deleted_at.is_(None))
        if status is not None:
            q = q.where(Article.status == status)
        if article_type is not None:
            q = q.where(Article.article_type == article_type)
        if tag is not None:
            q = q.where(
                exists(
                    select(ArticleTag.article_id)
                    .join(Tag, Tag.id == ArticleTag.tag_id)
                    .where(
                        ArticleTag.article_id == Article.id,
                        func.lower(Tag.name) == tag.lower().strip(),
                    )
                )
            )
        q = q.order_by(Article.published_at.desc().nulls_last(), Article.id.desc()).limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_tags_for_articles(
        self, db: AsyncSession, article_ids: list[int]
    ) -> dict[int, list[Tag]]:
        result = await db.execute(
            select(ArticleTag.article_id, Tag)
            .join(Tag, Tag.id == ArticleTag.tag_id)
            .where(ArticleTag.article_id.in_(article_ids))
        )
        groups: dict[int, list[Tag]] = {aid: [] for aid in article_ids}
        for row in result:
            groups[row.article_id].append(row.Tag)
        return groups

    async def get_tags_for_article(
        self, db: AsyncSession, article_id: int
    ) -> list[Tag]:
        return (await self.get_tags_for_articles(db, [article_id]))[article_id]

    async def get_by_broadcast_id(self, db: AsyncSession, broadcast_id: int) -> Article | None:
        result = await db.execute(
            select(Article).where(
                Article.broadcast_id == broadcast_id,
                Article.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
