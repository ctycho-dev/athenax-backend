from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.article.model import Article, ArticleCategory
from app.domain.category.model import Category
from app.enums.enums import ArticleStatus, ArticleType
from app.exceptions.exceptions import NotFoundError


class ArticleRepository(BaseRepository[Article]):
    def __init__(self) -> None:
        super().__init__(Article)

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Article:
        result = await db.execute(select(Article).where(Article.slug == slug))
        article = result.scalar_one_or_none()
        if article is None:
            raise NotFoundError(f"Article with slug '{slug}' not found")
        return article

    async def get_all_filtered(
        self,
        db: AsyncSession,
        status: ArticleStatus | None,
        article_type: ArticleType | None,
        category_id: int | None,
        limit: int,
        offset: int,
    ) -> list[Article]:
        q = select(Article)
        if status is not None:
            q = q.where(Article.status == status)
        if article_type is not None:
            q = q.where(Article.article_type == article_type)
        if category_id is not None:
            q = q.where(
                exists(
                    select(ArticleCategory.article_id).where(
                        ArticleCategory.article_id == Article.id,
                        ArticleCategory.category_id == category_id,
                    )
                )
            )
        q = q.order_by(Article.published_at.desc().nulls_last(), Article.id.desc()).limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_categories_for_articles(
        self, db: AsyncSession, article_ids: list[int]
    ) -> dict[int, list[Category]]:
        result = await db.execute(
            select(ArticleCategory.article_id, Category)
            .join(Category, Category.id == ArticleCategory.category_id)
            .where(ArticleCategory.article_id.in_(article_ids))
        )
        groups: dict[int, list[Category]] = {aid: [] for aid in article_ids}
        for row in result:
            groups[row.article_id].append(row.Category)
        return groups

    async def get_categories_for_article(
        self, db: AsyncSession, article_id: int
    ) -> list[Category]:
        return (await self.get_categories_for_articles(db, [article_id]))[article_id]
