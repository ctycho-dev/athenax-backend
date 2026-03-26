from datetime import datetime
import pytest
import pytest_asyncio
from typing import AsyncGenerator, cast
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from app.main import app
from app.database.connection import Base
from app.api.dependencies import get_db, get_current_user, get_email_service
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.infrastructure.email.service import EmailDeliveryError

pytest_plugins = [
    "tests.integration.fixtures.user",
]

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_analyser_db"


class FakeEmailService:
    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []
        self.fail_verification = False
        self.fail_password_reset = False

    async def send_verification_email(self, email: str, name: str, token: str) -> None:
        if self.fail_verification:
            raise EmailDeliveryError("verification delivery failed")
        self.sent_emails.append(
            {
                "type": "verification",
                "email": email,
                "name": name,
                "token": token,
            }
        )

    async def send_password_reset_email(self, email: str, name: str, token: str) -> None:
        if self.fail_password_reset:
            raise EmailDeliveryError("password reset delivery failed")
        self.sent_emails.append(
            {
                "type": "password_reset",
                "email": email,
                "name": name,
                "token": token,
            }
        )


class ClientWithEmail(AsyncClient):
    fake_email_service: FakeEmailService


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


@pytest.fixture(scope="session")
def session_factory(test_engine):
    """Create session factory once per session."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(loop_scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a plain async database session for setup tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[ClientWithEmail, None]:
    """Create test client. Each API call gets its own session."""
    mock_user = UserOutSchema(
        id=1,
        name="Test User",
        email="test@example.com",
        role=UserRole.USER,
        verified=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    async def override_get_db():
        async with session_factory() as session:
            yield session
    
    async def override_get_current_user():
        return mock_user

    fake_email_service = FakeEmailService()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_email_service] = lambda: fake_email_service
    
    from app.middleware.rate_limiter import limiter
    limiter.enabled = False
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_client = cast(ClientWithEmail, ac)
        test_client.fake_email_service = fake_email_service
        yield test_client
    
    app.dependency_overrides.clear()
    limiter.enabled = True
