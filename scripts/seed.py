import asyncio
from app.database.connection import db_manager
from app.database.fixtures import seed_categories


async def main():
    db_manager.init_engine()
    async with db_manager.session_scope() as session:
        await seed_categories(session)
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
