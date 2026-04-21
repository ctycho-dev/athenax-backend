import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_categories
from app.common.permissions import assert_can_modify, is_admin, is_owner
from app.domain.category.repository import CategoryRepository
from app.domain.paper.model import PaperCategory
from app.domain.paper.repository import PaperRepository
from app.domain.paper.schema import (
    PaperCreateSchema,
    PaperOutSchema,
    PaperUpdateSchema,
    PaperVerificationStatusUpdateSchema,
    VoteOutSchema,
)
from app.domain.user.schema import UserOutSchema
from app.enums.enums import PaperStatus, PaperVerificationStatus
from app.exceptions.exceptions import NotFoundError
from app.utils.slug import generate_slug


class PaperService:
    def __init__(self, repo: PaperRepository, category_repo: CategoryRepository):
        self.repo = repo
        self.category_repo = category_repo

    async def create(
        self,
        db: AsyncSession,
        data: PaperCreateSchema,
        current_user: UserOutSchema,
    ) -> PaperOutSchema:
        payload = data.model_dump()
        category_ids = payload.pop("category_ids", [])

        payload["created_by_id"] = current_user.id
        payload["slug"] = generate_slug(data.title)
        if payload.get("status") == PaperStatus.PUBLISHED:
            payload["published_at"] = datetime.now(timezone.utc)

        paper = await self.repo.create(db, payload, current_user_id=current_user.id)

        await sync_categories(db, self.category_repo, PaperCategory.__table__, "paper_id", paper.id, category_ids)

        await db.commit()
        await db.refresh(paper)
        return await self._to_schema(db, paper, current_user=current_user)

    async def list_papers(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        verification_status: PaperVerificationStatus | None = None,
        paper_status: PaperStatus | None = None,
        current_user: UserOutSchema | None = None,
        owner_only: bool = False,
    ) -> list[PaperOutSchema]:
        user_id: int | None = None
        if owner_only and current_user is not None:
            user_id = current_user.id
        elif current_user is None or not is_admin(current_user):
            verification_status = PaperVerificationStatus.APPROVED
        papers = await self.repo.get_all_by_verification_status(db, verification_status, limit=limit, offset=offset, user_id=user_id, paper_status=paper_status)
        if not papers:
            return []
        paper_ids = [p.id for p in papers]
        tasks = [
            self.repo.get_vote_counts(db, paper_ids),
            self.repo.get_categories_for_papers(db, paper_ids),
        ]
        if current_user:
            tasks.append(self.repo.get_user_votes(db, paper_ids, current_user.id))
        gathered = await asyncio.gather(*tasks)
        vote_counts, categories_map = gathered[0], gathered[1]
        user_votes: set[int] = gathered[2] if current_user else set()
        results = []
        for paper in papers:
            out = PaperOutSchema.model_validate(paper, from_attributes=True)
            out.vote_count = vote_counts[paper.id]
            out.category_ids = [c.id for c in categories_map[paper.id]]
            if current_user:
                out.voted = paper.id in user_votes
            results.append(out)
        return results

    async def get_by_id(
        self, db: AsyncSession, paper_id: int, current_user: UserOutSchema | None = None
    ) -> PaperOutSchema:
        paper = await self.repo.get_by_id(db, paper_id)
        if paper.verification_status != PaperVerificationStatus.APPROVED:
            if current_user is None or (not is_admin(current_user) and not is_owner(paper, current_user)):
                raise NotFoundError(f"Paper with id '{paper_id}' not found")
        return await self._to_schema(db, paper, current_user=current_user)

    async def get_by_slug(
        self, db: AsyncSession, slug: str, current_user: UserOutSchema | None = None
    ) -> PaperOutSchema:
        paper = await self.repo.get_by_slug(db, slug)
        if paper.verification_status != PaperVerificationStatus.APPROVED:
            if current_user is None or (not is_admin(current_user) and not is_owner(paper, current_user)):
                raise NotFoundError(f"Paper with slug '{slug}' not found")
        return await self._to_schema(db, paper, current_user=current_user)

    async def update(
        self,
        db: AsyncSession,
        paper_id: int,
        data: PaperUpdateSchema,
        current_user: UserOutSchema,
    ) -> PaperOutSchema:
        paper = await self.repo.get_by_id(db, paper_id)
        assert_can_modify(paper, current_user)

        payload = data.model_dump(exclude_unset=True)
        category_ids = payload.pop("category_ids", None)

        if "title" in payload:
            payload["slug"] = generate_slug(payload["title"])

        if "status" in payload:
            new_status = payload["status"]
            if new_status == PaperStatus.PUBLISHED and paper.status != PaperStatus.PUBLISHED:
                payload["published_at"] = datetime.now(timezone.utc)
            elif new_status != PaperStatus.PUBLISHED:
                payload["published_at"] = None

        paper = await self.repo.update(db, paper_id, payload, current_user_id=current_user.id)

        if category_ids is not None:
            await sync_categories(db, self.category_repo, PaperCategory.__table__, "paper_id", paper_id, category_ids)

        await db.commit()
        await db.refresh(paper)
        return await self._to_schema(db, paper)

    async def delete_by_id(
        self,
        db: AsyncSession,
        paper_id: int,
        current_user: UserOutSchema,
    ) -> None:
        paper = await self.repo.get_by_id(db, paper_id)
        assert_can_modify(paper, current_user)
        await self.repo.delete_by_id(db, paper_id)
        await db.commit()

    async def update_verification_status(
        self,
        db: AsyncSession,
        paper_id: int,
        data: PaperVerificationStatusUpdateSchema,
    ) -> PaperOutSchema:
        await self.repo.get_by_id(db, paper_id)
        paper = await self.repo.update(db, paper_id, {"verification_status": data.verification_status}, current_user_id=None)
        await db.commit()
        await db.refresh(paper)
        return await self._to_schema(db, paper)

    async def vote(
        self,
        db: AsyncSession,
        paper_id: int,
        voted: bool,
        current_user: UserOutSchema,
    ) -> VoteOutSchema:
        await self.repo.get_by_id(db, paper_id)

        if voted:
            await self.repo.add_vote(db, paper_id, current_user.id)
        else:
            await self.repo.remove_vote(db, paper_id, current_user.id)

        await db.commit()
        vote_count = await self.repo.get_vote_count(db, paper_id)
        return VoteOutSchema(paper_id=paper_id, vote_count=vote_count)

    async def get_related(
        self,
        db: AsyncSession,
        paper_id: int,
        limit: int,
        offset: int,
    ) -> list[PaperOutSchema]:
        paper = await self.repo.get_by_id_with_status_check(
            db, paper_id, required_verification_status=PaperVerificationStatus.APPROVED
        )
        categories = await self.repo.get_categories_for_paper(db, paper_id)
        category_ids = [c.id for c in categories]

        papers = await self.repo.get_related(
            db,
            paper_id=paper_id,
            product_id=paper.product_id,
            category_ids=category_ids,
            limit=limit,
            offset=offset,
        )
        if not papers:
            papers = await self.repo.get_latest(db, exclude_paper_id=paper_id, limit=limit, offset=offset)
        if not papers:
            return []
        ids = [p.id for p in papers]
        vote_counts = await self.repo.get_vote_counts(db, ids)
        categories_map = await self.repo.get_categories_for_papers(db, ids)
        results = []
        for p in papers:
            out = PaperOutSchema.model_validate(p, from_attributes=True)
            out.vote_count = vote_counts[p.id]
            out.category_ids = [c.id for c in categories_map[p.id]]
            results.append(out)
        return results

    async def _to_schema(self, db: AsyncSession, paper, current_user: UserOutSchema | None = None) -> PaperOutSchema:
        tasks = [
            self.repo.get_categories_for_paper(db, paper.id),
            self.repo.get_vote_count(db, paper.id),
        ]
        if current_user:
            tasks.append(self.repo.get_user_votes(db, [paper.id], current_user.id))
        gathered = await asyncio.gather(*tasks)
        categories, vote_count = gathered[0], gathered[1]
        result = PaperOutSchema.model_validate(paper, from_attributes=True)
        result.category_ids = [c.id for c in categories]
        result.vote_count = vote_count
        if current_user:
            result.voted = paper.id in gathered[2]
        return result

