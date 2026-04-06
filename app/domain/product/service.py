from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_categories
from app.common.permissions import assert_can_modify, is_admin
from app.domain.category.repository import CategoryRepository
from app.domain.category.schema import CategoryOutSchema
from app.domain.product.model import ProductCategory
from app.domain.product.repository import ProductRepository
from app.domain.product.schema import (
    CommentCreateSchema,
    CommentOutSchema,
    CommentUpdateSchema,
    ProductCreateSchema,
    ProductOutSchema,
    ProductUpdateSchema,
    ToggleOutSchema,
    VerifyProductRequestSchema,
)
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ProductStatus
from app.exceptions.exceptions import NotFoundError
from app.utils.slug import generate_slug


class ProductService:
    def __init__(self, repo: ProductRepository, category_repo: CategoryRepository):
        self.repo = repo
        self.category_repo = category_repo

    async def create(
        self,
        db: AsyncSession,
        data: ProductCreateSchema,
        current_user: UserOutSchema,
    ) -> ProductOutSchema:
        payload = data.model_dump()
        category_ids = payload.pop("category_ids", [])

        payload["user_id"] = current_user.id
        payload["slug"] = generate_slug(data.name, max_length=150)

        product = await self.repo.create(db, payload, current_user_id=current_user.id)

        await sync_categories(db, self.category_repo, ProductCategory.__table__, "product_id", product.id, category_ids)

        await db.commit()
        await db.refresh(product)
        return await self._to_schema(db, product)

    async def list(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        status: ProductStatus | None = None,
        current_user: UserOutSchema | None = None,
    ) -> list[ProductOutSchema]:
        # Non-admins can only ever see approved products regardless of requested status
        if current_user is None or not is_admin(current_user):
            status = ProductStatus.APPROVED
        products = await self.repo.get_all_by_status(db, status, limit=limit, offset=offset)
        if not products:
            return []
        product_ids = [p.id for p in products]
        vote_counts, bookmark_counts, investor_interest_counts, categories_map = await asyncio.gather(
            self.repo.get_vote_counts(db, product_ids),
            self.repo.get_bookmark_counts(db, product_ids),
            self.repo.get_investor_interest_counts(db, product_ids),
            self.repo.get_categories_for_products(db, product_ids),
        )
        results = []
        for product in products:
            out = ProductOutSchema.model_validate(product, from_attributes=True)
            out.vote_count = vote_counts[product.id]
            out.bookmark_count = bookmark_counts[product.id]
            out.investor_interest_count = investor_interest_counts[product.id]
            out.categories = [
                CategoryOutSchema.model_validate(c, from_attributes=True)
                for c in categories_map[product.id]
            ]
            results.append(out)
        return results

    async def get_by_id(self, db: AsyncSession, product_id: int) -> ProductOutSchema:
        product = await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        return await self._to_schema(db, product)

    async def update(
        self,
        db: AsyncSession,
        product_id: int,
        data: ProductUpdateSchema,
        current_user: UserOutSchema,
    ) -> ProductOutSchema:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)

        payload = data.model_dump(exclude_unset=True)
        category_ids = payload.pop("category_ids", None)

        product = await self.repo.update(db, product_id, payload, current_user_id=current_user.id)

        if category_ids is not None:
            await sync_categories(db, self.category_repo, ProductCategory.__table__, "product_id", product_id, category_ids)

        await db.commit()
        await db.refresh(product)
        return await self._to_schema(db, product)

    async def delete_by_id(
        self,
        db: AsyncSession,
        product_id: int,
        current_user: UserOutSchema,
    ) -> None:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        await self.repo.delete_by_id(db, product_id)
        await db.commit()

    async def toggle_vote(
        self, db: AsyncSession, product_id: int, toggled: bool, current_user: UserOutSchema
    ) -> ToggleOutSchema:
        return await self._toggle(
            db, product_id, toggled,
            self.repo.add_vote, self.repo.remove_vote, self.repo.get_vote_count,
            current_user,
        )

    async def toggle_bookmark(
        self, db: AsyncSession, product_id: int, toggled: bool, current_user: UserOutSchema
    ) -> ToggleOutSchema:
        return await self._toggle(
            db, product_id, toggled,
            self.repo.add_bookmark, self.repo.remove_bookmark, self.repo.get_bookmark_count,
            current_user,
        )

    async def toggle_investor_interest(
        self, db: AsyncSession, product_id: int, toggled: bool, current_user: UserOutSchema
    ) -> ToggleOutSchema:
        return await self._toggle(
            db, product_id, toggled,
            self.repo.add_investor_interest, self.repo.remove_investor_interest, self.repo.get_investor_interest_count,
            current_user,
        )

    async def _toggle(self, db, product_id, toggled, add_fn, remove_fn, count_fn, current_user) -> ToggleOutSchema:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        if toggled:
            await add_fn(db, product_id, current_user.id)
        else:
            await remove_fn(db, product_id, current_user.id)
        await db.commit()
        count = await count_fn(db, product_id)
        return ToggleOutSchema(product_id=product_id, count=count)

    async def list_comments(
        self, db: AsyncSession, product_id: int, limit: int, offset: int
    ) -> list[CommentOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        comments = await self.repo.get_comments(db, product_id, limit, offset)
        return [CommentOutSchema.model_validate(c, from_attributes=True) for c in comments]

    async def create_comment(
        self,
        db: AsyncSession,
        product_id: int,
        data: CommentCreateSchema,
        current_user: UserOutSchema,
    ) -> CommentOutSchema:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        comment = await self.repo.create_comment(db, product_id, current_user.id, data.text)
        await db.commit()
        await db.refresh(comment)
        return CommentOutSchema.model_validate(comment, from_attributes=True)

    async def update_comment(
        self,
        db: AsyncSession,
        product_id: int,
        comment_id: int,
        data: CommentUpdateSchema,
        current_user: UserOutSchema,
    ) -> CommentOutSchema:
        comment = await self.repo.get_comment_by_id(db, comment_id)
        if comment is None or comment.product_id != product_id:
            raise NotFoundError("Comment not found")
        assert_can_modify(comment, current_user)
        comment = await self.repo.update_comment(db, comment, data.text)
        await db.commit()
        await db.refresh(comment)
        return CommentOutSchema.model_validate(comment, from_attributes=True)

    async def delete_comment(
        self,
        db: AsyncSession,
        product_id: int,
        comment_id: int,
        current_user: UserOutSchema,
    ) -> None:
        comment = await self.repo.get_comment_by_id(db, comment_id)
        if comment is None or comment.product_id != product_id:
            raise NotFoundError("Comment not found")
        assert_can_modify(comment, current_user)
        await self.repo.delete_comment(db, comment_id)
        await db.commit()

    async def verify(
        self,
        db: AsyncSession,
        product_id: int,
        data: VerifyProductRequestSchema,
        current_user: UserOutSchema,
    ) -> ProductOutSchema:
        await self.repo.get_by_id(db, product_id)
        product = await self.repo.update(db, product_id, {"status": data.status}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(product)
        return await self._to_schema(db, product)

    async def _to_schema(self, db: AsyncSession, product) -> ProductOutSchema:
        categories, vote_count, bookmark_count, investor_interest_count = await asyncio.gather(
            self.repo.get_categories_for_product(db, product.id),
            self.repo.get_vote_count(db, product.id),
            self.repo.get_bookmark_count(db, product.id),
            self.repo.get_investor_interest_count(db, product.id),
        )
        result = ProductOutSchema.model_validate(product, from_attributes=True)
        result.categories = [
            CategoryOutSchema.model_validate(c, from_attributes=True) for c in categories
        ]
        result.vote_count = vote_count
        result.bookmark_count = bookmark_count
        result.investor_interest_count = investor_interest_count
        return result

