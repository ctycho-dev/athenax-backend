import asyncio
from sqlalchemy import select
from app.database.connection import db_manager
from app.domain.category.model import Category

SEED_CATEGORIES = [
    "AI & Agents",
    "Robotics",
    "Biotech",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Climate & Energy",
]


async def main():
    db_manager.init_engine()
    async with db_manager.session_scope() as session:
        result = await session.execute(select(Category.name))
        existing = set(result.scalars().all())

        to_insert = [name for name in SEED_CATEGORIES if name not in existing]
        if to_insert:
            for name in to_insert:
                session.add(Category(name=name))
            await session.commit()
            print(f"Seeded {len(to_insert)} categories: {to_insert}")
        else:
            print("All categories already exist, nothing to seed.")

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
