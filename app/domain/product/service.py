from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_categories
from app.common.permissions import assert_can_modify, is_admin, is_owner
from app.common.schema import PaginatedSchema
from app.domain.category.repository import CategoryRepository
from app.domain.product.model import ProductCategory
from app.domain.product.repository import (
    CommentRepository, ProductRepository,
    ProductLinkRepository, ProductMediaRepository, ProductTeamRepository,
    ProductBackerRepository, ProductVoiceRepository, BountyRepository,
)
from app.domain.paper.schema import PaperSummarySchema
from app.domain.product.schema import (
    CommentCreateSchema,
    CommentOutSchema,
    CommentPinSchema,
    CommentUpdateSchema,
    FounderSummarySchema,
    ProductCreateSchema,
    ProductListSchema,
    ProductOutSchema,
    ProductReleaseStatsSchema,
    ProductStatusUpdateSchema,
    ProductSummarySchema,
    ProductUpdateSchema,
    ReleasePeriodSchema,
    ToggleOutSchema,
    ProductLinkCreateSchema, ProductLinkUpdateSchema, ProductLinkOutSchema,
    ProductMediaCreateSchema, ProductMediaUpdateSchema, ProductMediaOutSchema,
    TeamMemberCreateSchema, TeamMemberUpdateSchema, TeamMemberStatusUpdateSchema, TeamMemberOutSchema,
    ProductBackerCreateSchema, ProductBackerOutSchema,
    ProductVoiceCreateSchema, ProductVoiceUpdateSchema, ProductVoiceOutSchema,
    BountyCreateSchema, BountyUpdateSchema, BountyOutSchema,
)
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ProductDateFilter, ProductSortBy, ProductStatus, VerificationStatus
from app.exceptions.exceptions import NotFoundError
from app.utils.slug import generate_slug


@dataclass
class _InteractionData:
    vote_counts: dict[int, int]
    bookmark_counts: dict[int, int]
    investor_interest_counts: dict[int, int]
    categories_map: dict[int, list]
    user_votes: set[int] = field(default_factory=set)
    user_bookmarks: set[int] = field(default_factory=set)
    user_interests: set[int] = field(default_factory=set)


class ProductService:
    def __init__(
        self,
        repo: ProductRepository,
        category_repo: CategoryRepository,
        comment_repo: CommentRepository,
        link_repo: ProductLinkRepository,
        media_repo: ProductMediaRepository,
        team_repo: ProductTeamRepository,
        backer_repo: ProductBackerRepository,
        voice_repo: ProductVoiceRepository,
        bounty_repo: BountyRepository,
    ):
        self.repo = repo
        self.category_repo = category_repo
        self.comment_repo = comment_repo
        self.link_repo = link_repo
        self.media_repo = media_repo
        self.team_repo = team_repo
        self.backer_repo = backer_repo
        self.voice_repo = voice_repo
        self.bounty_repo = bounty_repo

    async def _fetch_interaction_data(
        self,
        db: AsyncSession,
        product_ids: list[int],
        current_user: UserOutSchema | None,
    ) -> _InteractionData:
        tasks = [
            self.repo.get_vote_counts(db, product_ids),
            self.repo.get_bookmark_counts(db, product_ids),
            self.repo.get_investor_interest_counts(db, product_ids),
            self.repo.get_categories_for_products(db, product_ids),
        ]
        if current_user:
            tasks += [
                self.repo.get_user_votes(db, product_ids, current_user.id),
                self.repo.get_user_bookmarks(db, product_ids, current_user.id),
                self.repo.get_user_investor_interests(db, product_ids, current_user.id),
            ]
        gathered = await asyncio.gather(*tasks)
        data = _InteractionData(*gathered[:4])
        if current_user:
            data.user_votes, data.user_bookmarks, data.user_interests = gathered[4], gathered[5], gathered[6]
        return data

    async def get_release_stats(self, db: AsyncSession) -> ProductReleaseStatsSchema:
        stats = await self.repo.get_release_stats(db)
        return ProductReleaseStatsSchema(releases=ReleasePeriodSchema(**stats))

    async def create(
        self,
        db: AsyncSession,
        data: ProductCreateSchema,
        current_user: UserOutSchema,
    ) -> ProductOutSchema:
        payload = data.model_dump()
        category_ids = payload.pop("category_ids", [])

        founders = payload.get("founders")
        payload["founders"] = json.dumps(founders) if founders else None

        payload["created_by_id"] = current_user.id
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
        owner_only: bool = False,
        category_id: int | None = None,
        date_filter: ProductDateFilter | None = None,
        sort_by: ProductSortBy | None = None,
    ) -> PaginatedSchema[ProductListSchema]:
        user_id: int | None = None
        if owner_only and current_user is not None:
            # Founder viewing their own products — allow any status, filter by user
            user_id = current_user.id
        elif current_user is None or not is_admin(current_user):
            # Non-admins can only see approved products
            status = ProductStatus.APPROVED
        products = await self.repo.get_all_by_status(
            db, status, limit=limit, offset=offset, user_id=user_id,
            category_id=category_id, date_filter=date_filter, sort_by=sort_by,
        )
        total = await self.repo.count_by_status(
            db, status, user_id=user_id,
            category_id=category_id, date_filter=date_filter,
        )

        if not products:
            return PaginatedSchema(items=[], total=total)

        product_ids = [p.id for p in products]
        ix = await self._fetch_interaction_data(db, product_ids, current_user)

        results = []
        for product in products:
            out = ProductListSchema.model_validate(product, from_attributes=True)
            out.vote_count = ix.vote_counts[product.id]
            out.bookmark_count = ix.bookmark_counts[product.id]
            out.investor_interest_count = ix.investor_interest_counts[product.id]
            out.category_ids = [c.id for c in ix.categories_map[product.id]]
            if current_user:
                out.bookmarked = product.id in ix.user_bookmarks
            results.append(out)
        return PaginatedSchema(items=results, total=total)

    async def get_by_id(
        self, db: AsyncSession, product_id: int, current_user: UserOutSchema | None = None
    ) -> ProductOutSchema:
        product = await self.repo.get_by_id(db, product_id)
        if product.status != ProductStatus.APPROVED:
            if current_user is None or (not is_admin(current_user) and not is_owner(product, current_user)):
                raise NotFoundError(f"Product with id '{product_id}' not found")
        return await self._to_schema(db, product, current_user=current_user)

    async def get_by_slug(
        self, db: AsyncSession, slug: str, current_user: UserOutSchema | None = None
    ) -> ProductOutSchema:
        product = await self.repo.get_by_slug(db, slug)
        if not product:
            raise NotFoundError(f"Product with slug '{slug}' not found")
        if product.status != ProductStatus.APPROVED:
            if current_user is None or (not is_admin(current_user) and not is_owner(product, current_user)):
                raise NotFoundError(f"Product with slug '{slug}' not found")
        return await self._to_schema(db, product, current_user=current_user)

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

        if "founders" in payload:
            founders = payload["founders"]
            payload["founders"] = json.dumps(founders) if founders else None

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

    async def list_voted(
        self, db: AsyncSession, limit: int, offset: int, current_user: UserOutSchema
    ) -> list[ProductSummarySchema]:
        product_ids = await self.repo.get_voted_product_ids_by_user(db, current_user.id, limit, offset)
        return await self._to_summary_list(db, product_ids)

    async def list_bookmarked(
        self, db: AsyncSession, limit: int, offset: int, current_user: UserOutSchema
    ) -> list[ProductSummarySchema]:
        product_ids = await self.repo.get_bookmarked_product_ids_by_user(db, current_user.id, limit, offset)
        return await self._to_summary_list(db, product_ids)

    async def _to_summary_list(
        self, db: AsyncSession, product_ids: list[int]
    ) -> list[ProductSummarySchema]:
        if not product_ids:
            return []
        products, vote_counts, bookmark_counts, categories_map = await asyncio.gather(
            self.repo.get_by_ids(db, product_ids),
            self.repo.get_vote_counts(db, product_ids),
            self.repo.get_bookmark_counts(db, product_ids),
            self.repo.get_categories_for_products(db, product_ids),
        )
        results = []
        for product in products:
            out = ProductSummarySchema.model_validate(product, from_attributes=True)
            out.vote_count = vote_counts[product.id]
            out.bookmark_count = bookmark_counts[product.id]
            out.category_ids = [c.id for c in categories_map[product.id]]
            results.append(out)
        return results

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

    async def _toggle(
        self,
        db: AsyncSession,
        product_id: int,
        toggled: bool,
        add_fn: Callable,
        remove_fn: Callable,
        count_fn: Callable,
        current_user: UserOutSchema,
    ) -> ToggleOutSchema:
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
        comments = await self.comment_repo.get_by_product(db, product_id, limit, offset)
        return [CommentOutSchema.model_validate(c, from_attributes=True) for c in comments]

    async def create_comment(
        self,
        db: AsyncSession,
        product_id: int,
        data: CommentCreateSchema,
        current_user: UserOutSchema,
    ) -> CommentOutSchema:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        comment = await self.comment_repo.create(db, {"product_id": product_id, "created_by_id": current_user.id, "text": data.text})
        await db.commit()
        return CommentOutSchema.model_validate(comment, from_attributes=True)

    async def update_comment(
        self,
        db: AsyncSession,
        product_id: int,
        comment_id: int,
        data: CommentUpdateSchema,
        current_user: UserOutSchema,
    ) -> CommentOutSchema:
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if comment.product_id != product_id:
            raise NotFoundError("Comment not found")
        assert_can_modify(comment, current_user)
        comment = await self.comment_repo.update_instance(db, comment, {"text": data.text})
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
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if comment.product_id != product_id:
            raise NotFoundError("Comment not found")
        assert_can_modify(comment, current_user)
        await self.comment_repo.delete_by_id(db, comment_id)
        await db.commit()

    async def pin_comment(
        self,
        db: AsyncSession,
        product_id: int,
        comment_id: int,
        data: CommentPinSchema,
        current_user: UserOutSchema,
    ) -> CommentOutSchema:
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if comment.product_id != product_id:
            raise NotFoundError("Comment not found")
        comment = await self.comment_repo.update_instance(db, comment, {"pinned": data.pinned})
        await db.commit()
        await db.refresh(comment)
        return CommentOutSchema.model_validate(comment, from_attributes=True)

    async def update_status(
        self,
        db: AsyncSession,
        product_id: int,
        data: ProductStatusUpdateSchema,
        current_user: UserOutSchema,
    ) -> ProductOutSchema:
        product = await self.repo.update(db, product_id, {"status": data.status}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(product)
        return await self._to_schema(db, product)

    # -------------------------
    # Product Links
    # -------------------------

    async def list_links(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductLinkOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        links = await self.link_repo.get_by_product_id(db, product_id)
        return [ProductLinkOutSchema.model_validate(l, from_attributes=True) for l in links]

    async def create_link(
        self, db: AsyncSession, product_id: int, data: ProductLinkCreateSchema, current_user: UserOutSchema
    ) -> ProductLinkOutSchema:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        link = await self.link_repo.create(db, {**data.model_dump(), "product_id": product_id}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(link)
        return ProductLinkOutSchema.model_validate(link, from_attributes=True)

    async def update_link(
        self, db: AsyncSession, product_id: int, link_id: int, data: ProductLinkUpdateSchema, current_user: UserOutSchema
    ) -> ProductLinkOutSchema:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        link = await self.link_repo.get_by_id(db, link_id)
        if link.product_id != product_id:
            raise NotFoundError("Link not found")
        link = await self.link_repo.update(db, link_id, data.model_dump(exclude_unset=True), current_user_id=current_user.id)
        await db.commit()
        await db.refresh(link)
        return ProductLinkOutSchema.model_validate(link, from_attributes=True)

    async def delete_link(
        self, db: AsyncSession, product_id: int, link_id: int, current_user: UserOutSchema
    ) -> None:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        link = await self.link_repo.get_by_id(db, link_id)
        if link.product_id != product_id:
            raise NotFoundError("Link not found")
        await self.link_repo.delete_by_id(db, link_id)
        await db.commit()

    # -------------------------
    # Product Media
    # -------------------------

    async def list_media(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductMediaOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        media = await self.media_repo.get_by_product_id(db, product_id)
        return [ProductMediaOutSchema.model_validate(m, from_attributes=True) for m in media]

    async def create_media(
        self, db: AsyncSession, product_id: int, data: ProductMediaCreateSchema, current_user: UserOutSchema
    ) -> ProductMediaOutSchema:
        await self.repo.get_by_id(db, product_id)
        media = await self.media_repo.create(db, {**data.model_dump(), "product_id": product_id}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(media)
        return ProductMediaOutSchema.model_validate(media, from_attributes=True)

    async def update_media(
        self, db: AsyncSession, product_id: int, media_id: int, data: ProductMediaUpdateSchema, current_user: UserOutSchema
    ) -> ProductMediaOutSchema:
        media = await self.media_repo.get_by_id(db, media_id)
        if media.product_id != product_id:
            raise NotFoundError("Media not found")
        media = await self.media_repo.update(db, media_id, data.model_dump(exclude_unset=True), current_user_id=current_user.id)
        await db.commit()
        await db.refresh(media)
        return ProductMediaOutSchema.model_validate(media, from_attributes=True)

    async def delete_media(
        self, db: AsyncSession, product_id: int, media_id: int, current_user: UserOutSchema
    ) -> None:
        media = await self.media_repo.get_by_id(db, media_id)
        if media.product_id != product_id:
            raise NotFoundError("Media not found")
        await self.media_repo.delete_by_id(db, media_id)
        await db.commit()

    # -------------------------
    # Product Team
    # -------------------------

    async def list_team(
        self, db: AsyncSession, product_id: int, current_user: UserOutSchema | None = None
    ) -> list[TeamMemberOutSchema]:
        product = await self.repo.get_by_id(db, product_id)
        if product.status != ProductStatus.APPROVED:
            if not current_user or (not is_admin(current_user) and not is_owner(product, current_user)):
                raise NotFoundError(f"Product with id '{product_id}' not found")
        status_filter = None if (current_user and (is_admin(current_user) or is_owner(product, current_user))) else VerificationStatus.APPROVED
        members = await self.team_repo.get_by_product_id(db, product_id, status=status_filter)
        return [TeamMemberOutSchema.model_validate(m, from_attributes=True) for m in members]

    async def create_team_member(
        self, db: AsyncSession, product_id: int, data: TeamMemberCreateSchema, current_user: UserOutSchema
    ) -> TeamMemberOutSchema:
        await self.repo.get_by_id(db, product_id)
        payload = {**data.model_dump(), "product_id": product_id, "status": VerificationStatus.APPROVED}
        member = await self.team_repo.create(db, payload, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(member)
        return TeamMemberOutSchema.model_validate(member, from_attributes=True)

    async def update_team_member(
        self, db: AsyncSession, product_id: int, member_id: int, data: TeamMemberUpdateSchema, current_user: UserOutSchema
    ) -> TeamMemberOutSchema:
        member = await self.team_repo.get_by_id(db, member_id)
        if member.product_id != product_id:
            raise NotFoundError("Team member not found")
        member = await self.team_repo.update(db, member_id, data.model_dump(exclude_unset=True), current_user_id=current_user.id)
        await db.commit()
        await db.refresh(member)
        return TeamMemberOutSchema.model_validate(member, from_attributes=True)

    async def update_team_member_status(
        self, db: AsyncSession, product_id: int, member_id: int, data: TeamMemberStatusUpdateSchema, current_user: UserOutSchema
    ) -> TeamMemberOutSchema:
        member = await self.team_repo.get_by_id(db, member_id)
        if member.product_id != product_id:
            raise NotFoundError("Team member not found")
        member = await self.team_repo.update(
            db, member_id, {"status": data.status, "reviewed_by_id": current_user.id}, current_user_id=current_user.id
        )
        await db.commit()
        await db.refresh(member)
        return TeamMemberOutSchema.model_validate(member, from_attributes=True)

    async def delete_team_member(
        self, db: AsyncSession, product_id: int, member_id: int, current_user: UserOutSchema
    ) -> None:
        member = await self.team_repo.get_by_id(db, member_id)
        if member.product_id != product_id:
            raise NotFoundError("Team member not found")
        await self.team_repo.delete_by_id(db, member_id)
        await db.commit()

    # -------------------------
    # Product Backers
    # -------------------------

    async def list_backers(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductBackerOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        backers = await self.backer_repo.get_by_product_id(db, product_id)
        return [ProductBackerOutSchema.model_validate(b, from_attributes=True) for b in backers]

    async def create_backer(
        self, db: AsyncSession, product_id: int, data: ProductBackerCreateSchema, current_user: UserOutSchema
    ) -> ProductBackerOutSchema:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        backer = await self.backer_repo.create(db, {**data.model_dump(), "product_id": product_id}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(backer)
        return ProductBackerOutSchema.model_validate(backer, from_attributes=True)

    async def delete_backer(
        self, db: AsyncSession, product_id: int, backer_id: int, current_user: UserOutSchema
    ) -> None:
        product = await self.repo.get_by_id(db, product_id)
        assert_can_modify(product, current_user)
        backer = await self.backer_repo.get_by_id(db, backer_id)
        if backer.product_id != product_id:
            raise NotFoundError("Backer not found")
        await self.backer_repo.delete_by_id(db, backer_id)
        await db.commit()

    # -------------------------
    # Product Voices
    # -------------------------

    async def list_voices(
        self, db: AsyncSession, product_id: int
    ) -> list[ProductVoiceOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        voices = await self.voice_repo.get_by_product_id(db, product_id)
        return [ProductVoiceOutSchema.model_validate(v, from_attributes=True) for v in voices]

    async def create_voice(
        self, db: AsyncSession, product_id: int, data: ProductVoiceCreateSchema, current_user: UserOutSchema
    ) -> ProductVoiceOutSchema:
        await self.repo.get_by_id(db, product_id)
        voice = await self.voice_repo.create(db, {**data.model_dump(), "product_id": product_id}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(voice)
        return ProductVoiceOutSchema.model_validate(voice, from_attributes=True)

    async def update_voice(
        self, db: AsyncSession, product_id: int, voice_id: int, data: ProductVoiceUpdateSchema, current_user: UserOutSchema
    ) -> ProductVoiceOutSchema:
        voice = await self.voice_repo.get_by_id(db, voice_id)
        if voice.product_id != product_id:
            raise NotFoundError("Voice not found")
        voice = await self.voice_repo.update(db, voice_id, data.model_dump(exclude_unset=True), current_user_id=current_user.id)
        await db.commit()
        await db.refresh(voice)
        return ProductVoiceOutSchema.model_validate(voice, from_attributes=True)

    async def delete_voice(
        self, db: AsyncSession, product_id: int, voice_id: int, current_user: UserOutSchema
    ) -> None:
        voice = await self.voice_repo.get_by_id(db, voice_id)
        if voice.product_id != product_id:
            raise NotFoundError("Voice not found")
        await self.voice_repo.delete_by_id(db, voice_id)
        await db.commit()

    # -------------------------
    # Bounties
    # -------------------------

    async def list_bounties(
        self, db: AsyncSession, product_id: int
    ) -> list[BountyOutSchema]:
        await self.repo.get_by_id_with_status_check(db, product_id, required_status=ProductStatus.APPROVED)
        bounties = await self.bounty_repo.get_by_product_id(db, product_id)
        return [BountyOutSchema.model_validate(b, from_attributes=True) for b in bounties]

    async def create_bounty(
        self, db: AsyncSession, product_id: int, data: BountyCreateSchema, current_user: UserOutSchema
    ) -> BountyOutSchema:
        await self.repo.get_by_id(db, product_id)
        bounty = await self.bounty_repo.create(db, {**data.model_dump(), "product_id": product_id}, current_user_id=current_user.id)
        await db.commit()
        await db.refresh(bounty)
        return BountyOutSchema.model_validate(bounty, from_attributes=True)

    async def update_bounty(
        self, db: AsyncSession, product_id: int, bounty_id: int, data: BountyUpdateSchema, current_user: UserOutSchema
    ) -> BountyOutSchema:
        bounty = await self.bounty_repo.get_by_id(db, bounty_id)
        if bounty.product_id != product_id:
            raise NotFoundError("Bounty not found")
        bounty = await self.bounty_repo.update(db, bounty_id, data.model_dump(exclude_unset=True), current_user_id=current_user.id)
        await db.commit()
        await db.refresh(bounty)
        return BountyOutSchema.model_validate(bounty, from_attributes=True)

    async def delete_bounty(
        self, db: AsyncSession, product_id: int, bounty_id: int, current_user: UserOutSchema
    ) -> None:
        bounty = await self.bounty_repo.get_by_id(db, bounty_id)
        if bounty.product_id != product_id:
            raise NotFoundError("Bounty not found")
        await self.bounty_repo.delete_by_id(db, bounty_id)
        await db.commit()

    async def _to_schema(
        self, db: AsyncSession, product, current_user: UserOutSchema | None = None
    ) -> ProductOutSchema:
        ix, papers, founder_data, links, media, team, backers, voices, bounties = await asyncio.gather(
            self._fetch_interaction_data(db, [product.id], current_user),
            self.repo.get_papers_for_product(db, product.id),
            self.repo.get_founder_summary(db, product.created_by_id),
            self.link_repo.get_by_product_id(db, product.id),
            self.media_repo.get_by_product_id(db, product.id),
            self.team_repo.get_by_product_id(db, product.id, status=VerificationStatus.APPROVED),
            self.backer_repo.get_by_product_id(db, product.id),
            self.voice_repo.get_by_product_id(db, product.id),
            self.bounty_repo.get_by_product_id(db, product.id),
        )

        result = ProductOutSchema.model_validate(product, from_attributes=True)
        result.category_ids = [c.id for c in ix.categories_map[product.id]]
        result.vote_count = ix.vote_counts[product.id]
        result.bookmark_count = ix.bookmark_counts[product.id]
        result.investor_interest_count = ix.investor_interest_counts[product.id]
        result.papers = [PaperSummarySchema.model_validate(p, from_attributes=True) for p in papers]
        result.founder = FounderSummarySchema(**founder_data) if founder_data else None
        result.links = [ProductLinkOutSchema.model_validate(l, from_attributes=True) for l in links]
        result.media = [ProductMediaOutSchema.model_validate(m, from_attributes=True) for m in media]
        result.team = [TeamMemberOutSchema.model_validate(m, from_attributes=True) for m in team]
        result.backers = [ProductBackerOutSchema.model_validate(b, from_attributes=True) for b in backers]
        result.voices = [ProductVoiceOutSchema.model_validate(v, from_attributes=True) for v in voices]
        result.bounties = [BountyOutSchema.model_validate(b, from_attributes=True) for b in bounties]
        if current_user:
            result.voted = product.id in ix.user_votes
            result.bookmarked = product.id in ix.user_bookmarks
            result.interested = product.id in ix.user_interests
        return result

