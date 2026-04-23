from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.domain.lab.model import Lab
from app.domain.paper.model import Paper
from app.domain.university.model import University
from app.domain.user.model import ResearcherProfile, User
from app.enums.enums import PaperStatus, ProductDateFilter, ProductSortBy, ProductStatus
from app.exceptions.exceptions import NotFoundError
from app.domain.product.model import (
    Product,
    ProductBookmark,
    ProductCategory,
    ProductComment,
    ProductInvestorInterest,
    ProductVote,
)


class CommentRepository(BaseRepository[ProductComment]):
    def __init__(self) -> None:
        super().__init__(ProductComment)

    async def get_by_product(
        self, db: AsyncSession, product_id: int, limit: int, offset: int
    ) -> list[ProductComment]:
        result = await db.execute(
            select(ProductComment)
            .where(ProductComment.product_id == product_id)
            .order_by(ProductComment.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())



class ProductRepository(BaseRepository[Product]):
    def __init__(self) -> None:
        super().__init__(Product)

    # -------------------------
    # Stats
    # -------------------------
    async def get_release_stats(self, db: AsyncSession) -> dict[str, int]:
        now = datetime.now(tz=timezone.utc)
        cutoffs = {
            "total": None,
            "today": now - timedelta(hours=24),
            "this_week": now - timedelta(weeks=1),
            "this_month": now - timedelta(days=30),
        }
        result = {}
        for key, cutoff in cutoffs.items():
            q = select(func.count()).where(Product.status == ProductStatus.APPROVED)
            if cutoff is not None:
                q = q.where(Product.created_at >= cutoff)
            row = await db.execute(q)
            result[key] = row.scalar_one()
        return result

    # -------------------------
    # Status filtering
    # -------------------------
    _DATE_FILTER_DELTAS: dict[ProductDateFilter, timedelta] = {
        ProductDateFilter.TODAY: timedelta(hours=24),
        ProductDateFilter.THIS_WEEK: timedelta(weeks=1),
        ProductDateFilter.THIS_MONTH: timedelta(days=30),
        ProductDateFilter.THIS_YEAR: timedelta(days=365),
    }

    def _build_status_query(
        self,
        status: ProductStatus | None = None,
        user_id: int | None = None,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
        sort_by: ProductSortBy | None = None,
    ):
        vote_subq = None
        if sort_by == ProductSortBy.TOP:
            vote_subq = (
                select(
                    ProductVote.product_id,
                    func.count().label("vote_count"),
                )
                .group_by(ProductVote.product_id)
                .subquery()
            )
            q = select(Product).outerjoin(vote_subq, vote_subq.c.product_id == Product.id)
        else:
            q = select(Product)

        if status is not None:
            q = q.where(Product.status == status)
        if user_id is not None:
            q = q.where(Product.created_by_id == user_id)
        if category_id is not None:
            q = q.where(
                Product.id.in_(
                    select(ProductCategory.product_id).where(
                        ProductCategory.category_id == category_id
                    )
                )
            )
        if date_filter is not None:
            cutoff = datetime.now(tz=timezone.utc) - self._DATE_FILTER_DELTAS[date_filter]
            q = q.where(Product.created_at >= cutoff)

        if vote_subq is not None:
            q = q.order_by(func.coalesce(vote_subq.c.vote_count, 0).desc(), Product.created_at.desc())
        else:
            q = q.order_by(Product.created_at.desc())

        return q, vote_subq

    async def get_all_by_status(
        self,
        db: AsyncSession,
        status: ProductStatus | None,
        limit: int,
        offset: int,
        user_id: int | None = None,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
        sort_by: ProductSortBy | None = None,
    ) -> list[Product]:
        q, _ = self._build_status_query(status, user_id, category_id, date_filter, sort_by)
        q = q.limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        db: AsyncSession,
        status: ProductStatus | None = None,
        user_id: int | None = None,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
    ) -> int:
        q, _ = self._build_status_query(status, user_id, category_id, date_filter)
        q = select(func.count()).select_from(q.subquery())
        result = await db.execute(q)
        return result.scalar() or 0

    async def get_by_ids(self, db: AsyncSession, product_ids: list[int]) -> list[Product]:
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products_by_id = {p.id: p for p in result.scalars().all()}
        return [products_by_id[pid] for pid in product_ids if pid in products_by_id]

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Product | None:
        result = await db.execute(select(Product).where(Product.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id_with_status_check(
        self, db: AsyncSession, product_id: int, required_status: ProductStatus | None = None
    ) -> Product:
        result = await db.execute(select(Product).where(Product.id == product_id))
        instance = result.scalar_one_or_none()
        if not instance:
            raise NotFoundError(f"Product with ID {product_id} not found")
        if required_status is not None and instance.status != required_status:
            raise NotFoundError(f"Product with ID {product_id} not found") # Don't reveal existence of product if status doesn't match 
        return instance

    # -------------------------
    # Categories
    # -------------------------
    async def get_categories_for_products(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, list[Category]]:
        result = await db.execute(
            select(ProductCategory.product_id, Category)
            .join(Category, Category.id == ProductCategory.category_id)
            .where(ProductCategory.product_id.in_(product_ids))
        )
        groups: dict[int, list[Category]] = {pid: [] for pid in product_ids}
        for row in result:
            groups[row.product_id].append(row.Category)
        return groups

    async def get_categories_for_product(
        self, db: AsyncSession, product_id: int
    ) -> list[Category]:
        return (await self.get_categories_for_products(db, [product_id]))[product_id]

    async def get_papers_for_product(self, db: AsyncSession, product_id: int) -> list[Paper]:
        result = await db.execute(
            select(Paper)
            .where(Paper.product_id == product_id, Paper.status == PaperStatus.PUBLISHED)
            .order_by(Paper.published_at.desc())
        )
        return list(result.scalars().all())

    async def get_founder_summary(self, db: AsyncSession, user_id: int) -> dict | None:
        result = await db.execute(
            select(
                User.id,
                User.name,
                Lab.name.label("lab_name"),
                University.name.label("university_name"),
            )
            .outerjoin(ResearcherProfile, ResearcherProfile.user_id == User.id)
            .outerjoin(Lab, Lab.id == ResearcherProfile.lab_id)
            .outerjoin(University, University.id == Lab.university_id)
            .where(User.id == user_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "lab_name": row.lab_name,
            "university_name": row.university_name,
        }

    # -------------------------
    # Votes
    # -------------------------
    async def get_vote_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductVote.product_id, func.count().label("cnt"))
            .where(ProductVote.product_id.in_(product_ids))
            .group_by(ProductVote.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_vote_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_vote_counts(db, [product_id]))[product_id]

    async def get_user_votes(
        self, db: AsyncSession, product_ids: list[int], user_id: int
    ) -> set[int]:
        result = await db.execute(
            select(ProductVote.product_id)
            .where(
                ProductVote.product_id.in_(product_ids),
                ProductVote.user_id == user_id,
            )
        )
        return {row.product_id for row in result}

    async def get_voted_product_ids_by_user(
        self, db: AsyncSession, user_id: int, limit: int, offset: int
    ) -> list[int]:
        result = await db.execute(
            select(ProductVote.product_id)
            .where(ProductVote.user_id == user_id)
            .order_by(ProductVote.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [row.product_id for row in result]

    async def add_vote(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductVote)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_vote(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductVote).where(
                ProductVote.product_id == product_id,
                ProductVote.user_id == user_id,
            )
        )

    # -------------------------
    # Bookmarks
    # -------------------------
    async def get_bookmark_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductBookmark.product_id, func.count().label("cnt"))
            .where(ProductBookmark.product_id.in_(product_ids))
            .group_by(ProductBookmark.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_bookmark_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_bookmark_counts(db, [product_id]))[product_id]

    async def get_user_bookmarks(
        self, db: AsyncSession, product_ids: list[int], user_id: int
    ) -> set[int]:
        result = await db.execute(
            select(ProductBookmark.product_id)
            .where(
                ProductBookmark.product_id.in_(product_ids),
                ProductBookmark.user_id == user_id,
            )
        )
        return {row.product_id for row in result}

    async def get_bookmarked_product_ids_by_user(
        self, db: AsyncSession, user_id: int, limit: int, offset: int
    ) -> list[int]:
        result = await db.execute(
            select(ProductBookmark.product_id)
            .where(ProductBookmark.user_id == user_id)
            .order_by(ProductBookmark.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [row.product_id for row in result]

    async def add_bookmark(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductBookmark)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_bookmark(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductBookmark).where(
                ProductBookmark.product_id == product_id,
                ProductBookmark.user_id == user_id,
            )
        )

    # -------------------------
    # Investor interests
    # -------------------------
    async def get_investor_interest_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductInvestorInterest.product_id, func.count().label("cnt"))
            .where(ProductInvestorInterest.product_id.in_(product_ids))
            .group_by(ProductInvestorInterest.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_investor_interest_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_investor_interest_counts(db, [product_id]))[product_id]

    async def get_user_investor_interests(
        self, db: AsyncSession, product_ids: list[int], user_id: int
    ) -> set[int]:
        result = await db.execute(
            select(ProductInvestorInterest.product_id)
            .where(
                ProductInvestorInterest.product_id.in_(product_ids),
                ProductInvestorInterest.user_id == user_id,
            )
        )
        return {row.product_id for row in result}

    async def add_investor_interest(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductInvestorInterest)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_investor_interest(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductInvestorInterest).where(
                ProductInvestorInterest.product_id == product_id,
                ProductInvestorInterest.user_id == user_id,
            )
        )

