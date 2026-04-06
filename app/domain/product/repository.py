from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.enums.enums import ProductStatus
from app.exceptions.exceptions import NotFoundError
from app.domain.product.model import (
    Product,
    ProductBookmark,
    ProductCategory,
    ProductComment,
    ProductInvestorInterest,
    ProductVote,
)


class ProductRepository(BaseRepository[Product]):
    def __init__(self) -> None:
        super().__init__(Product)

    # -------------------------
    # Status filtering
    # -------------------------
    async def get_all_by_status(
        self, db: AsyncSession, status: ProductStatus | None, limit: int, offset: int
    ) -> list[Product]:
        q = select(Product)
        if status is not None:
            q = q.where(Product.status == status)
        q = q.limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

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
            select(ProductCategory.__table__.c.product_id, Category)
            .join(Category, Category.id == ProductCategory.__table__.c.category_id)
            .where(ProductCategory.__table__.c.product_id.in_(product_ids))
        )
        groups: dict[int, list[Category]] = {pid: [] for pid in product_ids}
        for row in result:
            groups[row.product_id].append(row.Category)
        return groups

    async def get_categories_for_product(
        self, db: AsyncSession, product_id: int
    ) -> list[Category]:
        return (await self.get_categories_for_products(db, [product_id]))[product_id]

    # -------------------------
    # Votes
    # -------------------------
    async def get_vote_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductVote.__table__.c.product_id, func.count().label("cnt"))
            .where(ProductVote.__table__.c.product_id.in_(product_ids))
            .group_by(ProductVote.__table__.c.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_vote_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_vote_counts(db, [product_id]))[product_id]

    async def add_vote(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductVote.__table__)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_vote(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductVote.__table__).where(
                ProductVote.__table__.c.product_id == product_id,
                ProductVote.__table__.c.user_id == user_id,
            )
        )

    # -------------------------
    # Bookmarks
    # -------------------------
    async def get_bookmark_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductBookmark.__table__.c.product_id, func.count().label("cnt"))
            .where(ProductBookmark.__table__.c.product_id.in_(product_ids))
            .group_by(ProductBookmark.__table__.c.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_bookmark_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_bookmark_counts(db, [product_id]))[product_id]

    async def add_bookmark(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductBookmark.__table__)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_bookmark(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductBookmark.__table__).where(
                ProductBookmark.__table__.c.product_id == product_id,
                ProductBookmark.__table__.c.user_id == user_id,
            )
        )

    # -------------------------
    # Investor interests
    # -------------------------
    async def get_investor_interest_counts(
        self, db: AsyncSession, product_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(ProductInvestorInterest.__table__.c.product_id, func.count().label("cnt"))
            .where(ProductInvestorInterest.__table__.c.product_id.in_(product_ids))
            .group_by(ProductInvestorInterest.__table__.c.product_id)
        )
        counts = {row.product_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in product_ids}

    async def get_investor_interest_count(self, db: AsyncSession, product_id: int) -> int:
        return (await self.get_investor_interest_counts(db, [product_id]))[product_id]

    async def add_investor_interest(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(ProductInvestorInterest.__table__)
            .values(product_id=product_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_investor_interest(self, db: AsyncSession, product_id: int, user_id: int) -> None:
        await db.execute(
            delete(ProductInvestorInterest.__table__).where(
                ProductInvestorInterest.__table__.c.product_id == product_id,
                ProductInvestorInterest.__table__.c.user_id == user_id,
            )
        )

    # -------------------------
    # Comments
    # -------------------------
    async def get_comments(
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

    async def get_comment_by_id(
        self, db: AsyncSession, comment_id: int
    ) -> ProductComment | None:
        result = await db.execute(
            select(ProductComment).where(ProductComment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def create_comment(
        self, db: AsyncSession, product_id: int, user_id: int, text: str
    ) -> ProductComment:
        comment = ProductComment(product_id=product_id, user_id=user_id, text=text)
        db.add(comment)
        await db.flush()
        await db.refresh(comment)
        return comment

    async def update_comment(
        self, db: AsyncSession, comment: ProductComment, text: str
    ) -> ProductComment:
        comment.text = text
        await db.flush()
        await db.refresh(comment)
        return comment

    async def delete_comment(self, db: AsyncSession, comment_id: int) -> None:
        await db.execute(
            delete(ProductComment).where(ProductComment.id == comment_id)
        )
