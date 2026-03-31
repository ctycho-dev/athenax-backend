from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db_utils import sync_association
from app.domain.category.repository import CategoryRepository
from app.domain.category.schema import CategoryOutSchema
from app.domain.paper.model import PaperCategory
from app.domain.paper.repository import PaperRepository
from app.domain.paper.schema import (
    PaperCreateSchema,
    PaperOutSchema,
    PaperUpdateSchema,
    VoteOutSchema,
)
from app.domain.user.schema import UserOutSchema
from app.enums.enums import PaperStatus, UserRole
from app.exceptions.exceptions import ValidationError
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

        if category_ids:
            await self.category_repo.assert_exist(db, category_ids)

        payload["user_id"] = current_user.id
        payload["slug"] = generate_slug(data.title)

        if payload.get("status") == PaperStatus.PUBLISHED:
            payload["published_at"] = datetime.now(timezone.utc)

        paper = await self.repo.create(db, payload, current_user_id=current_user.id)

        await sync_association(
            db,
            PaperCategory.__table__,
            "paper_id",
            paper.id,
            "category_id",
            set(category_ids),
        )

        await db.commit()
        await db.refresh(paper)
        return await self._to_schema(db, paper)

    async def list(self, db: AsyncSession, limit: int, offset: int) -> list[PaperOutSchema]:
        papers = await self.repo.get_all(db, limit=limit, offset=offset)
        if not papers:
            return []
        paper_ids = [p.id for p in papers]
        vote_counts = await self.repo.get_vote_counts(db, paper_ids)
        categories_map = await self.repo.get_categories_for_papers(db, paper_ids)
        results = []
        for paper in papers:
            out = PaperOutSchema.model_validate(paper, from_attributes=True)
            out.vote_count = vote_counts[paper.id]
            out.categories = [
                CategoryOutSchema.model_validate(c, from_attributes=True)
                for c in categories_map[paper.id]
            ]
            results.append(out)
        return results

    async def get_by_id(self, db: AsyncSession, paper_id: int) -> PaperOutSchema:
        paper = await self.repo.get_by_id(db, paper_id)
        return await self._to_schema(db, paper)

    async def update(
        self,
        db: AsyncSession,
        paper_id: int,
        data: PaperUpdateSchema,
        current_user: UserOutSchema,
    ) -> PaperOutSchema:
        paper = await self.repo.get_by_id(db, paper_id)
        self._assert_can_modify(paper, current_user)

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
            await self.category_repo.assert_exist(db, category_ids)
            await sync_association(
                db,
                PaperCategory.__table__,
                "paper_id",
                paper_id,
                "category_id",
                set(category_ids),
            )

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
        self._assert_can_modify(paper, current_user)
        await self.repo.delete_by_id(db, paper_id)
        await db.commit()

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

    async def _to_schema(self, db: AsyncSession, paper) -> PaperOutSchema:
        categories = await self.repo.get_categories_for_paper(db, paper.id)
        vote_count = await self.repo.get_vote_count(db, paper.id)
        result = PaperOutSchema.model_validate(paper, from_attributes=True)
        result.categories = [
            CategoryOutSchema.model_validate(c, from_attributes=True) for c in categories
        ]
        result.vote_count = vote_count
        return result

    def _assert_can_modify(self, paper, current_user: UserOutSchema) -> None:
        if current_user.role == UserRole.ADMIN:
            return
        if paper.user_id != current_user.id:
            raise ValidationError("You do not have permission to modify this paper")
