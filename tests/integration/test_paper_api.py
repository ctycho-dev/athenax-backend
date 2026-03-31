from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.domain.category.model import Category
from app.domain.user.model import User
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ClientWithEmail


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_users():
    """Insert users with id=1 and id=2 needed by paper FK constraints."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            pg_insert(User)
            .values(
                [
                    {"id": 1, "name": "Researcher", "email": "researcher@test.com", "password_hash": "x", "role": UserRole.RESEARCHER, "verified": True},
                    {"id": 2, "name": "Other", "email": "other@test.com", "password_hash": "x", "role": UserRole.RESEARCHER, "verified": True},
                ]
            )
            .on_conflict_do_nothing()
        )
        await session.commit()
    await engine.dispose()


def build_mock_user(role: UserRole, user_id: int = 1) -> UserOutSchema:
    return UserOutSchema(
        id=user_id,
        name="Test User",
        email=f"user{user_id}@example.com",
        role=role,
        verified=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


PAPER_PAYLOAD = {
    "title": "My Research Paper",
    "abstract": "A study on AI.",
    "status": "draft",
    "sourceType": "editor",
    "content": "Full paper content here.",
    "categoryIds": [],
}


@pytest.mark.asyncio
class TestPaperAPI:

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    async def test_list_papers_is_public(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_unauthorized():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_user] = override_unauthorized
        try:
            response = await client.get("/api/v1/paper")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_paper_not_found(self, client: ClientWithEmail):
        response = await client.get("/api/v1/paper/999999")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # RBAC — create
    # ------------------------------------------------------------------

    async def test_create_paper_forbidden_for_regular_user(self, client: ClientWithEmail):
        response = await client.post("/api/v1/paper", json=PAPER_PAYLOAD)
        assert response.status_code == 403
        assert response.json()["detail"] == "Researcher role required"

    async def test_create_paper_allowed_for_researcher(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_researcher():
            return build_mock_user(UserRole.RESEARCHER)

        app.dependency_overrides[get_current_user] = override_researcher
        try:
            response = await client.post("/api/v1/paper", json=PAPER_PAYLOAD)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == PAPER_PAYLOAD["title"]
        assert data["slug"] != ""
        assert data["userId"] == 1
        assert data["voteCount"] == 0

    async def test_create_paper_allowed_for_admin(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.post("/api/v1/paper", json=PAPER_PAYLOAD)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201

    async def test_create_paper_sets_published_at_when_published(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_researcher():
            return build_mock_user(UserRole.RESEARCHER)

        app.dependency_overrides[get_current_user] = override_researcher
        try:
            payload = {**PAPER_PAYLOAD, "status": "published"}
            response = await client.post("/api/v1/paper", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None

    async def test_create_paper_draft_has_no_published_at(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_researcher():
            return build_mock_user(UserRole.RESEARCHER)

        app.dependency_overrides[get_current_user] = override_researcher
        try:
            response = await client.post("/api/v1/paper", json=PAPER_PAYLOAD)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        assert response.json()["publishedAt"] is None

    async def test_create_paper_with_category_ids(self, client: ClientWithEmail, db_session):
        category_result = await db_session.execute(
            insert(Category).values(name="ML Research").returning(Category.id)
        )
        category_id = category_result.scalar_one()
        await db_session.commit()

        original = app.dependency_overrides[get_current_user]

        async def override_researcher():
            return build_mock_user(UserRole.RESEARCHER)

        app.dependency_overrides[get_current_user] = override_researcher
        try:
            payload = {**PAPER_PAYLOAD, "categoryIds": [category_id]}
            response = await client.post("/api/v1/paper", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        assert any(c["id"] == category_id for c in response.json()["categories"])

    async def test_create_paper_invalid_category_returns_404(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_researcher():
            return build_mock_user(UserRole.RESEARCHER)

        app.dependency_overrides[get_current_user] = override_researcher
        try:
            payload = {**PAPER_PAYLOAD, "categoryIds": [999999]}
            response = await client.post("/api/v1/paper", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    async def _create_paper_as_researcher(
        self, client: ClientWithEmail, user_id: int = 1
    ) -> int:
        original = app.dependency_overrides[get_current_user]

        async def override():
            return build_mock_user(UserRole.RESEARCHER, user_id=user_id)

        app.dependency_overrides[get_current_user] = override
        try:
            resp = await client.post("/api/v1/paper", json=PAPER_PAYLOAD)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert resp.status_code == 201
        return resp.json()["id"]

    # ------------------------------------------------------------------
    # Ownership / RBAC — update
    # ------------------------------------------------------------------

    async def test_owner_can_update_own_paper(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client, user_id=1)

        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.RESEARCHER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.patch(
                f"/api/v1/paper/{paper_id}", json={"abstract": "Updated abstract"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["abstract"] == "Updated abstract"

    async def test_non_owner_researcher_cannot_update_others_paper(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client, user_id=1)

        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.RESEARCHER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.patch(
                f"/api/v1/paper/{paper_id}", json={"abstract": "Hijacked"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_admin_can_update_any_paper(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client, user_id=1)

        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/paper/{paper_id}", json={"abstract": "Admin updated"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["abstract"] == "Admin updated"

    async def test_update_title_regenerates_slug(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client)
        original_slug = (await client.get(f"/api/v1/paper/{paper_id}")).json()["slug"]

        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.RESEARCHER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.patch(
                f"/api/v1/paper/{paper_id}", json={"title": "New Title For Paper"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["slug"] != original_slug
        assert "new-title-for-paper" in response.json()["slug"]

    async def test_update_status_to_published_sets_published_at(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client)

        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.RESEARCHER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.patch(
                f"/api/v1/paper/{paper_id}", json={"status": "published"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["publishedAt"] is not None

    # ------------------------------------------------------------------
    # Ownership / RBAC — delete
    # ------------------------------------------------------------------

    async def test_owner_can_delete_own_paper(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client, user_id=1)

        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.RESEARCHER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.delete(f"/api/v1/paper/{paper_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    async def test_non_owner_researcher_cannot_delete_others_paper(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client, user_id=1)

        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.RESEARCHER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.delete(f"/api/v1/paper/{paper_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------

    async def test_vote_adds_and_removes_vote(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client)

        response = await client.put(
            f"/api/v1/paper/{paper_id}/vote", json={"voted": True}
        )
        assert response.status_code == 200
        assert response.json()["voteCount"] == 1

        response = await client.put(
            f"/api/v1/paper/{paper_id}/vote", json={"voted": False}
        )
        assert response.status_code == 200
        assert response.json()["voteCount"] == 0

    async def test_duplicate_vote_is_idempotent(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client)

        await client.put(f"/api/v1/paper/{paper_id}/vote", json={"voted": True})
        response = await client.put(
            f"/api/v1/paper/{paper_id}/vote", json={"voted": True}
        )
        assert response.status_code == 200
        assert response.json()["voteCount"] == 1

    async def test_vote_on_missing_paper_returns_404(self, client: ClientWithEmail):
        response = await client.put(
            "/api/v1/paper/999999/vote", json={"voted": True}
        )
        assert response.status_code == 404

    async def test_vote_count_reflected_in_paper_response(self, client: ClientWithEmail):
        paper_id = await self._create_paper_as_researcher(client)

        await client.put(f"/api/v1/paper/{paper_id}/vote", json={"voted": True})
        response = await client.get(f"/api/v1/paper/{paper_id}")

        assert response.status_code == 200
        assert response.json()["voteCount"] == 1
