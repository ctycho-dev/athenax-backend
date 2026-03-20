from datetime import datetime
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from app.main import app
from app.database.connection import Base
from app.api.dependencies import get_db, get_current_user
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole


TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_analyser_db"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create test database engine and tables once per test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
def session_factory(test_engine):
    """Create session factory once per session."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """Create test client. Each API call gets its own session."""
    mock_user = UserOutSchema(
        id=1,
        name="Test Admin",
        email="test@example.com",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now()
    )
    
    async def override_get_db():
        async with session_factory() as session:
            yield session
    
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    from app.middleware.rate_limiter import limiter
    limiter.enabled = False
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
    limiter.enabled = True
