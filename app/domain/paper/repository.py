from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.category.model import Category
from app.domain.paper.model import Paper, PaperCategory, PaperVote


class PaperRepository(BaseRepository[Paper]):
    def __init__(self) -> None:
        super().__init__(Paper)

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
