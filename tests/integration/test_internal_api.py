import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.domain.category.model import Category
from app.domain.user.model import User
from app.enums.enums import SYSTEM_USER_EMAIL, UserRole, VerificationStatus
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ClientWithEmail

INTERNAL_KEY = "test-internal-key"
HEADERS = {"X-Internal-Key": INTERNAL_KEY}

PARENT_CATEGORY_NAME = "Internal Test Category"
SUBCATEGORY_NAME = "Internal Test Subcategory"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_internal_data(test_engine):
    """Seed the system user plus a category/subcategory used by the by-name lookups."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            pg_insert(User)
            .values(
                name="System",
                email=SYSTEM_USER_EMAIL,
                password_hash="!",
                role=UserRole.SYSTEM,
                verified=False,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))

        parent_id = (
            await session.execute(
                select(Category.id).where(Category.name == PARENT_CATEGORY_NAME)
            )
        ).scalar()
        if parent_id is None:
            parent = Category(name=PARENT_CATEGORY_NAME, status=VerificationStatus.APPROVED.value)
            session.add(parent)
            await session.flush()
            parent_id = parent.id
            session.add(
                Category(
                    name=SUBCATEGORY_NAME,
                    parent_id=parent_id,
                    status=VerificationStatus.APPROVED.value,
                )
            )
        await session.commit()
    await engine.dispose()


@pytest.fixture(autouse=True)
def set_internal_key(monkeypatch):
    """verify_internal_key reads settings at call time, so patching the attribute is enough."""
    monkeypatch.setattr(settings.auth, "internal_api_key", INTERNAL_KEY)


async def _system_user_id() -> int:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        uid = (
            await session.execute(select(User.id).where(User.email == SYSTEM_USER_EMAIL))
        ).scalar_one()
    await engine.dispose()
    return uid


@pytest.mark.asyncio
class TestInternalAPI:

    # ------------------------------------------------------------------
    # Auth gating
    # ------------------------------------------------------------------

    async def test_create_product_missing_key(self, client: ClientWithEmail):
        resp = await client.post("/api/v1/internal/products", json={"name": "No Key Product"})
        assert resp.status_code == 401

    async def test_create_product_wrong_key(self, client: ClientWithEmail):
        resp = await client.post(
            "/api/v1/internal/products",
            json={"name": "Wrong Key Product"},
            headers={"X-Internal-Key": "nope"},
        )
        assert resp.status_code == 401

    # ------------------------------------------------------------------
    # Product create → attributed to system user, PENDING
    # ------------------------------------------------------------------

    async def test_create_product_attributed_to_system_user(self, client: ClientWithEmail):
        system_user_id = await _system_user_id()
        resp = await client.post(
            "/api/v1/internal/products",
            json={"name": "Internal Lookup Product"},
            headers=HEADERS,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["createdById"] == system_user_id
        assert body["status"].lower() == "pending"

    # ------------------------------------------------------------------
    # By-name lookups
    # ------------------------------------------------------------------

    async def test_get_category_by_name(self, client: ClientWithEmail):
        resp = await client.get(
            "/api/v1/internal/categories/by-name",
            params={"name": PARENT_CATEGORY_NAME.lower()},  # case-insensitive
            headers=HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == PARENT_CATEGORY_NAME
        assert body["parentId"] is None

    async def test_get_subcategory_by_name(self, client: ClientWithEmail):
        resp = await client.get(
            "/api/v1/internal/subcategories/by-name",
            params={"name": SUBCATEGORY_NAME},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == SUBCATEGORY_NAME
        assert body["parentId"] is not None

    async def test_get_category_by_name_unknown_404(self, client: ClientWithEmail):
        resp = await client.get(
            "/api/v1/internal/categories/by-name",
            params={"name": "Does Not Exist"},
            headers=HEADERS,
        )
        assert resp.status_code == 404

    async def test_get_product_by_name(self, client: ClientWithEmail):
        # Create first so the lookup has a target (case-insensitive match).
        await client.post(
            "/api/v1/internal/products",
            json={"name": "Findable Product"},
            headers=HEADERS,
        )
        resp = await client.get(
            "/api/v1/internal/products/by-name",
            params={"name": "findable product"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Findable Product"

    async def test_get_product_by_name_unknown_404(self, client: ClientWithEmail):
        resp = await client.get(
            "/api/v1/internal/products/by-name",
            params={"name": "ghost product"},
            headers=HEADERS,
        )
        assert resp.status_code == 404
