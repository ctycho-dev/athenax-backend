from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.domain.subscriber.model import Subscriber
from app.exceptions.exceptions import DatabaseError


class SubscriberRepository(BaseRepository[Subscriber]):
    def __init__(self) -> None:
        super().__init__(Subscriber)

    async def get_by_unsubscribe_token(self, db: AsyncSession, token: str) -> Subscriber | None:
        try:
            result = await db.execute(
                select(Subscriber).where(Subscriber.unsubscribe_token == token)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve Subscriber by token: {e}") from e

