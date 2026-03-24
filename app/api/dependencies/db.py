import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import db_manager


async def get_db():
    """
    FastAPI dependency to get a database session.
    """
    async with db_manager.session_scope() as session:
        yield session
