# app/database/connection.py
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from contextlib import asynccontextmanager
from app.core.logger import get_logger


logger = get_logger()

# Set up logging
# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Base for models
Base = declarative_base()


class DatabaseManager:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.async_session: async_sessionmaker | None = None

    def init_engine(self):
        """
        Initialize the async engine.
        """
        DATABASE_URL = settings.DATABASE_URL
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set")

        self.engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=20,
            pool_pre_ping=True,
            connect_args={"server_settings": {"application_name": "ai-assistant"}}
        )

        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
            # close_resets_only=False
        )

    async def create_all_tables(self):
        """
        Create all tables (use only for testing or first run).
        In production, use Alembic migrations instead.
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call init_engine() first.")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session_scope(self):
        """
        Provide a transactional scope for a series of operations.
        Usage: async with db_manager.session_scope() as session:
        """
        if not self.async_session:
            raise RuntimeError("Session not initialized. Call init_engine() first.")
        
        session = self.async_session()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self):
        """
        Dispose the engine.
        """
        if self.engine:
            await self.engine.dispose()


db_manager = DatabaseManager()
