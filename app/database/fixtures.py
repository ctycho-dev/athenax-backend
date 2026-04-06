from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.category.model import Category

logger = get_logger(__name__)

SEED_CATEGORIES = [
    "AI & Agents",
    "Robotics",
    "Biotech",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Climate & Energy",
]


async def seed_categories(session: AsyncSession) -> None:
    result = await session.execute(select(Category.name))
    existing = set(result.scalars().all())

    to_insert = [name for name in SEED_CATEGORIES if name not in existing]
    if not to_insert:
        return

    for name in to_insert:
        session.add(Category(name=name))

    await session.commit()
    logger.info("Seeded %d categories: %s", len(to_insert), to_insert)
