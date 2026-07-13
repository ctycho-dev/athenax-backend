from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, insert, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.domain.lab.model import Lab
from app.domain.paper.model import Paper
from app.domain.university.model import University
from app.domain.user.model import ResearcherProfile, User
from app.enums.enums import PaperStatus, ProductDateFilter, ProductSortBy, ProductStatus
from app.exceptions.exceptions import NotFoundError, ValidationError
from app.domain.product.model import (
    Product,
    ProductBookmark,
    ProductCategory,
    ProductComment,
    ProductInvestorInterest,
    ProductRelated,
    ProductSimilar,
    ProductVote,
    ProductLink,
    ProductMedia,
    ProductTeamMember,
    ProductBacker,
    ProductGrant,
    ProductVoice,
    Bounty,
)
from app.enums.enums import VerificationStatus


class CommentRepository(BaseRepository[ProductComment]):
    def __init__(self) -> None:
        super().__init__(ProductComment)

    async def get_by_product(
        self, db: AsyncSession, product_id: int, limit: int, offset: int
    ) -> list[ProductComment]:
        # Step 1: paginate root comments to determine which threads to load
        root_result = await db.execute(
            select(ProductComment.id, ProductComment.path)
            .where(
                ProductComment.product_id == product_id,
                ProductComment.parent_id.is_(None),
            )
            .order_by(ProductComment.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        roots = root_result.all()
        if not roots:
            return []

        root_paths = [row.path for row in roots if row.path is not None]
        if not root_paths:
            # Paths not yet backfilled — fall back to root-only fetch
            root_ids = [row.id for row in roots]
            result = await db.execute(
                select(ProductComment)
                .where(
                    ProductComment.product_id == product_id,
                    ProductComment.id.in_(root_ids),
                )
                .order_by(ProductComment.created_at.asc())
            )
            return list(result.scalars().all())

        # Step 2: fetch each root thread (root + all descendants) using ltree <@.
        # root_paths come from our own DB so interpolation is safe.
        path_array = "ARRAY[" + ", ".join(f"'{p}'::ltree" for p in root_paths) + "]"
        result = await db.execute(
            select(ProductComment)
            .where(
                ProductComment.product_id == product_id,
                text(f"path <@ ANY({path_array})"),
            )
            .order_by(ProductComment.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_root_comments(self, db: AsyncSession, product_id: int) -> int:
        result = await db.execute(
            select(func.count())
            .where(
                ProductComment.product_id == product_id,
                ProductComment.parent_id.is_(None),
            )
        )
        return result.scalar_one()

    async def has_descendants(self, db: AsyncSession, comment_id: int) -> bool:
        result = await db.execute(
            select(ProductComment.id)
            .where(ProductComment.parent_id == comment_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None



class ProductLinkRepository(BaseRepository[ProductLink]):
    def __init__(self) -> None:
        super().__init__(ProductLink)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductLink]:
        result = await db.execute(
            select(ProductLink)
            .where(ProductLink.product_id == product_id)
            .order_by(ProductLink.link_type.asc(), ProductLink.created_at.asc())
        )
        return list(result.scalars().all())


class ProductMediaRepository(BaseRepository[ProductMedia]):
    def __init__(self) -> None:
        super().__init__(ProductMedia)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductMedia]:
        result = await db.execute(
            select(ProductMedia)
            .where(ProductMedia.product_id == product_id)
            .order_by(ProductMedia.sort_order.asc(), ProductMedia.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_max_sort_order(self, db: AsyncSession, product_id: int) -> int:
        result = await db.execute(
            select(func.max(ProductMedia.sort_order))
            .where(ProductMedia.product_id == product_id)
        )
        return result.scalar_one_or_none() or 0


class ProductTeamRepository(BaseRepository[ProductTeamMember]):
    def __init__(self) -> None:
        super().__init__(ProductTeamMember)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int,
        status: VerificationStatus | None = None,
    ) -> list[ProductTeamMember]:
        q = select(ProductTeamMember).where(ProductTeamMember.product_id == product_id)
        if status is not None:
            q = q.where(ProductTeamMember.status == status)
        q = q.order_by(ProductTeamMember.created_at.asc())
        result = await db.execute(q)
        return list(result.scalars().all())


class ProductBackerRepository(BaseRepository[ProductBacker]):
    def __init__(self) -> None:
        super().__init__(ProductBacker)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductBacker]:
        result = await db.execute(
            select(ProductBacker)
            .where(ProductBacker.product_id == product_id)
            .order_by(ProductBacker.created_at.asc())
        )
        return list(result.scalars().all())


class ProductGrantRepository(BaseRepository[ProductGrant]):
    def __init__(self) -> None:
        super().__init__(ProductGrant)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductGrant]:
        result = await db.execute(
            select(ProductGrant)
            .where(ProductGrant.product_id == product_id)
            .order_by(ProductGrant.created_at.asc())
        )
        return list(result.scalars().all())


class ProductVoiceRepository(BaseRepository[ProductVoice]):
    def __init__(self) -> None:
        super().__init__(ProductVoice)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductVoice]:
        result = await db.execute(
            select(ProductVoice)
            .where(ProductVoice.product_id == product_id)
            .order_by(ProductVoice.sort_order.asc(), ProductVoice.created_at.asc())
        )
        return list(result.scalars().all())


class BountyRepository(BaseRepository[Bounty]):
    def __init__(self) -> None:
        super().__init__(Bounty)

    async def get_by_product_id(
        self, db: AsyncSession, product_id: int
    ) -> list[Bounty]:
        result = await db.execute(
            select(Bounty)
            .where(Bounty.product_id == product_id)
            .order_by(Bounty.created_at.desc())
        )
        return list(result.scalars().all())


class ProductRepository(BaseRepository[Product]):
    def __init__(self) -> None:
        super().__init__(Product)

    async def get_by_name(self, db: AsyncSession, name: str) -> Product | None:
        """Exact, case-insensitive lookup, excluding soft-deleted rows."""
        result = await db.execute(
            select(Product).where(
                func.lower(Product.name) == name.lower(),
                Product.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    # -------------------------
    # Stats
    # -------------------------
    async def get_release_stats(self, db: AsyncSession) -> dict[str, int]:
        now = datetime.now(tz=timezone.utc)
        # Exclude products in hidden categories (e.g. Nouns) so stats match the
        # default listed feed, which filters the same way via listed=True.
        hidden_product_ids = (
            select(ProductCategory.product_id)
            .join(Category, ProductCategory.category_id == Category.id)
            .where(Category.is_hidden_from_all == True)
        )
        # Cutoffs come from _period_cutoff so these counts match the list filters exactly.
        q = select(
            func.count().label("total"),
            func.count().filter(Product.created_at >= self._period_cutoff(now, ProductDateFilter.TODAY)).label("today"),
            func.count().filter(Product.created_at >= self._period_cutoff(now, ProductDateFilter.THIS_WEEK)).label("this_week"),
            func.count().filter(Product.created_at >= self._period_cutoff(now, ProductDateFilter.THIS_MONTH)).label("this_month"),
            func.count().filter(Product.created_at >= self._period_cutoff(now, ProductDateFilter.RECENT)).label("recent"),
        ).where(
            Product.status == ProductStatus.APPROVED,
            Product.deleted_at.is_(None),
            ~Product.id.in_(hidden_product_ids),
        )
        row = (await db.execute(q)).mappings().one()
        return dict(row)

    # -------------------------
    # Status filtering
    # -------------------------
    @staticmethod
    def _period_cutoff(now: datetime, period: ProductDateFilter) -> datetime:
        """Single source of truth for time-window cutoffs, shared by the list
        filter and the release stats so their counts never diverge."""
        if period == ProductDateFilter.TODAY:
            return now - timedelta(hours=24)
        if period == ProductDateFilter.THIS_WEEK:
            return now - timedelta(days=14)
        if period == ProductDateFilter.THIS_MONTH:
            return now - timedelta(days=30)
        if period == ProductDateFilter.RECENT:
            return now - timedelta(days=60)
        if period == ProductDateFilter.THIS_YEAR:
            return now - timedelta(days=365)
        raise ValueError(f"Unhandled date filter: {period}")

    def _build_status_query(
        self,
        status: ProductStatus | None = None,
        user_id: int | None = None,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
        sort_by: ProductSortBy | None = None,
        search: str | None = None,
        upvoted_by_user_id: int | None = None,
        listed: bool | None = None,
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
            cutoff = self._period_cutoff(datetime.now(tz=timezone.utc), date_filter)
            q = q.where(Product.created_at >= cutoff)
        if search and (search_text := search.strip()):
            q = q.where(Product.name.ilike(f"%{search_text}%"))
        if upvoted_by_user_id is not None:
            q = q.where(
                Product.id.in_(
                    select(ProductVote.product_id).where(ProductVote.user_id == upvoted_by_user_id)
                )
            )
        if listed is not None:
            hidden_product_ids = (
                select(ProductCategory.product_id)
                .join(Category, ProductCategory.category_id == Category.id)
                .where(Category.is_hidden_from_all == True)
            )
            if listed:
                q = q.where(~Product.id.in_(hidden_product_ids))
            else:
                q = q.where(Product.id.in_(hidden_product_ids))

        q = q.where(Product.deleted_at.is_(None))

        # Products launch (become publicly visible) when approved, not when submitted —
        # sort by that recency, falling back to created_at for never-approved rows.
        approved_or_created = func.coalesce(Product.approved_at, Product.created_at)
        if vote_subq is not None:
            q = q.order_by(func.coalesce(vote_subq.c.vote_count, 0).desc(), approved_or_created.desc())
        elif sort_by == ProductSortBy.OLDEST:
            q = q.order_by(approved_or_created.asc())
        else:
            q = q.order_by(approved_or_created.desc())

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
        search: str | None = None,
        upvoted_by_user_id: int | None = None,
        listed: bool | None = None,
    ) -> list[Product]:
        q, _ = self._build_status_query(status, user_id, category_id, date_filter, sort_by, search, upvoted_by_user_id, listed)
        # Summary list serializes these columns only — prune the `description` body and unused fields from the read.
        q = q.options(
            load_only(
                Product.slug, Product.name, Product.short_desc, Product.stage,
                Product.funding, Product.founded, Product.quality_badge,
                Product.logo, Product.status, Product.created_at, Product.updated_at,
                Product.approved_at,
            )
        ).limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        db: AsyncSession,
        status: ProductStatus | None = None,
        user_id: int | None = None,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
        search: str | None = None,
        upvoted_by_user_id: int | None = None,
        listed: bool | None = None,
    ) -> int:
        q, _ = self._build_status_query(status, user_id, category_id, date_filter, search=search, upvoted_by_user_id=upvoted_by_user_id, listed=listed)
        q = select(func.count()).select_from(q.subquery())
        result = await db.execute(q)
        return result.scalar() or 0

    async def get_by_ids(self, db: AsyncSession, product_ids: list[int]) -> list[Product]:
        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids), Product.deleted_at.is_(None))
        )
        products_by_id = {p.id: p for p in result.scalars().all()}
        return [products_by_id[pid] for pid in product_ids if pid in products_by_id]

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Product | None:
        result = await db.execute(
            select(Product).where(Product.slug == slug, Product.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_status_check(
        self, db: AsyncSession, product_id: int, required_status: ProductStatus | None = None
    ) -> Product:
        result = await db.execute(
            select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise NotFoundError(f"Product with ID {product_id} not found")
        if required_status is not None and instance.status != required_status:
            raise NotFoundError(f"Product with ID {product_id} not found")  # Don't reveal existence of product if status doesn't match
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

    async def get_product_ids_by_category_ids(
        self, db: AsyncSession, category_ids: list[int], exclude_ids: list[int], limit: int
    ) -> list[int]:
        approved_or_created = func.coalesce(Product.approved_at, Product.created_at)
        result = await db.execute(
            select(ProductCategory.product_id)
            .join(Product, Product.id == ProductCategory.product_id)
            .where(
                ProductCategory.category_id.in_(category_ids),
                ProductCategory.product_id.notin_(exclude_ids),
                Product.status == ProductStatus.APPROVED,
                Product.deleted_at.is_(None),
            )
            .group_by(ProductCategory.product_id, approved_or_created, Product.id)
            .order_by(approved_or_created.desc(), Product.id.desc())
            .limit(limit)
        )
        return [row.product_id for row in result]

    # -------------------------
    # Similar products (admin-curated, symmetric)
    # -------------------------
    async def get_curated_product_ids(self, db: AsyncSession, product_id: int) -> list[int]:
        """Both directions of the symmetric relation, oldest-curated first."""
        result = await db.execute(
            select(ProductSimilar.product_id, ProductSimilar.similar_product_id)
            .where(or_(ProductSimilar.product_id == product_id, ProductSimilar.similar_product_id == product_id))
            .order_by(ProductSimilar.created_at)
        )
        return [
            row.similar_product_id if row.product_id == product_id else row.product_id
            for row in result
        ]

    async def assert_similar_ids_valid(self, db: AsyncSession, product_id: int, similar_ids: list[int]) -> None:
        if product_id in similar_ids:
            raise ValidationError("A product cannot be marked similar to itself")
        if not similar_ids:
            return
        existing = await self.get_by_ids(db, similar_ids)
        if len(existing) != len(set(similar_ids)):
            raise NotFoundError("One or more similar products not found")

    async def sync_similar_products(self, db: AsyncSession, product_id: int, similar_ids: list[int]) -> None:
        """Replace product_id's full curated set. Each pair is normalized to canonical (min, max) order."""
        existing = set(await self.get_curated_product_ids(db, product_id))
        new_ids = set(similar_ids)
        to_add = new_ids - existing
        to_remove = existing - new_ids

        for rid in to_remove:
            lo, hi = min(product_id, rid), max(product_id, rid)
            await db.execute(
                delete(ProductSimilar).where(
                    ProductSimilar.product_id == lo, ProductSimilar.similar_product_id == hi
                )
            )
        for rid in to_add:
            lo, hi = min(product_id, rid), max(product_id, rid)
            await db.execute(insert(ProductSimilar).values(product_id=lo, similar_product_id=hi))
        await db.flush()

    # -------------------------
    # Related products (admin-curated, symmetric)
    # -------------------------
    async def get_curated_related_ids(self, db: AsyncSession, product_id: int) -> list[int]:
        """Both directions of the symmetric relation, oldest-curated first."""
        result = await db.execute(
            select(ProductRelated.product_id, ProductRelated.related_product_id)
            .where(or_(ProductRelated.product_id == product_id, ProductRelated.related_product_id == product_id))
            .order_by(ProductRelated.created_at)
        )
        return [
            row.related_product_id if row.product_id == product_id else row.product_id
            for row in result
        ]

    async def assert_related_ids_valid(self, db: AsyncSession, product_id: int, related_ids: list[int]) -> None:
        if product_id in related_ids:
            raise ValidationError("A product cannot be marked related to itself")
        if not related_ids:
            return
        existing = await self.get_by_ids(db, related_ids)
        if len(existing) != len(set(related_ids)):
            raise NotFoundError("One or more related products not found")

    async def sync_related_products(self, db: AsyncSession, product_id: int, related_ids: list[int]) -> None:
        """Replace product_id's full curated set. Each pair is normalized to canonical (min, max) order."""
        existing = set(await self.get_curated_related_ids(db, product_id))
        new_ids = set(related_ids)
        to_add = new_ids - existing
        to_remove = existing - new_ids

        for rid in to_remove:
            lo, hi = min(product_id, rid), max(product_id, rid)
            await db.execute(
                delete(ProductRelated).where(
                    ProductRelated.product_id == lo, ProductRelated.related_product_id == hi
                )
            )
        for rid in to_add:
            lo, hi = min(product_id, rid), max(product_id, rid)
            await db.execute(insert(ProductRelated).values(product_id=lo, related_product_id=hi))
        await db.flush()

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

    async def add_votes_bulk(
        self, db: AsyncSession, product_id: int, user_ids: list[int]
    ) -> None:
        if not user_ids:
            return
        await db.execute(
            pg_insert(ProductVote)
            .values([{"product_id": product_id, "user_id": uid} for uid in user_ids])
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

