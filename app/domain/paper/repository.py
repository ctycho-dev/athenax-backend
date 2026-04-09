from sqlalchemy import and_, delete, func, or_, select
from app.exceptions.exceptions import NotFoundError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.domain.paper.model import Paper, PaperCategory, PaperVote
from app.enums.enums import PaperVerificationStatus


class PaperRepository(BaseRepository[Paper]):
    def __init__(self) -> None:
        super().__init__(Paper)

    async def get_all_by_verification_status(
        self,
        db: AsyncSession,
        verification_status: PaperVerificationStatus | None,
        limit: int,
        offset: int,
        user_id: int | None = None,
    ) -> list[Paper]:
        q = select(Paper)
        if verification_status is not None:
            q = q.where(Paper.verification_status == verification_status)
        if user_id is not None:
            q = q.where(Paper.user_id == user_id)
        q = q.limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_latest(
        self,
        db: AsyncSession,
        exclude_paper_id: int,
        limit: int,
        offset: int,
    ) -> list[Paper]:
        q = (
            select(Paper)
            .where(Paper.verification_status == PaperVerificationStatus.APPROVED)
            .where(Paper.id != exclude_paper_id)
            .order_by(Paper.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_by_id_with_status_check(
        self, db: AsyncSession, paper_id: int, required_verification_status: PaperVerificationStatus | None = None
    ) -> Paper:
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        instance = result.scalar_one_or_none()
        if not instance:
            raise NotFoundError(f"Paper with ID {paper_id} not found")
        if required_verification_status is not None and instance.verification_status != required_verification_status:
            raise NotFoundError(f"Paper with ID {paper_id} not found")
        return instance

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Paper:
        result = await db.execute(select(Paper).where(Paper.slug == slug))
        paper = result.scalar_one_or_none()
        if paper is None:
            raise NotFoundError(f"Paper with slug '{slug}' not found")
        return paper

    async def get_categories_for_papers(
        self, db: AsyncSession, paper_ids: list[int]
    ) -> dict[int, list[Category]]:
        result = await db.execute(
            select(PaperCategory.__table__.c.paper_id, Category)
            .join(Category, Category.id == PaperCategory.__table__.c.category_id)
            .where(PaperCategory.__table__.c.paper_id.in_(paper_ids))
        )
        groups: dict[int, list[Category]] = {pid: [] for pid in paper_ids}
        for row in result:
            groups[row.paper_id].append(row.Category)
        return groups

    async def get_categories_for_paper(
        self, db: AsyncSession, paper_id: int
    ) -> list[Category]:
        return (await self.get_categories_for_papers(db, [paper_id]))[paper_id]

    async def get_user_votes(
        self, db: AsyncSession, paper_ids: list[int], user_id: int
    ) -> set[int]:
        result = await db.execute(
            select(PaperVote.__table__.c.paper_id)
            .where(PaperVote.__table__.c.paper_id.in_(paper_ids))
            .where(PaperVote.__table__.c.user_id == user_id)
        )
        return {row.paper_id for row in result}

    async def get_vote_counts(
        self, db: AsyncSession, paper_ids: list[int]
    ) -> dict[int, int]:
        result = await db.execute(
            select(PaperVote.__table__.c.paper_id, func.count().label("cnt"))
            .where(PaperVote.__table__.c.paper_id.in_(paper_ids))
            .group_by(PaperVote.__table__.c.paper_id)
        )
        counts = {row.paper_id: row.cnt for row in result}
        return {pid: counts.get(pid, 0) for pid in paper_ids}

    async def get_vote_count(self, db: AsyncSession, paper_id: int) -> int:
        return (await self.get_vote_counts(db, [paper_id]))[paper_id]

    async def add_vote(self, db: AsyncSession, paper_id: int, user_id: int) -> None:
        await db.execute(
            pg_insert(PaperVote.__table__)
            .values(paper_id=paper_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def remove_vote(self, db: AsyncSession, paper_id: int, user_id: int) -> None:
        await db.execute(
            delete(PaperVote.__table__).where(
                PaperVote.__table__.c.paper_id == paper_id,
                PaperVote.__table__.c.user_id == user_id,
            )
        )

    async def get_related(
        self,
        db: AsyncSession,
        paper_id: int,
        product_id: int | None,
        category_ids: list[int],
        limit: int,
        offset: int,
    ) -> list[Paper]:
        """Papers sharing at least one category OR the same product, excluding self."""
        conditions = []
        if category_ids:
            same_topic = (
                select(PaperCategory.__table__.c.paper_id)
                .where(PaperCategory.__table__.c.category_id.in_(category_ids))
                .where(PaperCategory.__table__.c.paper_id != paper_id)
                .scalar_subquery()
            )
            conditions.append(Paper.id.in_(same_topic))
        if product_id is not None:
            conditions.append(and_(Paper.product_id == product_id, Paper.id != paper_id))

        if not conditions:
            return []

        q = (
            select(Paper)
            .where(Paper.verification_status == PaperVerificationStatus.APPROVED)
            .where(Paper.id != paper_id)
            .where(or_(*conditions))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(q)
        return list(result.scalars().all())
