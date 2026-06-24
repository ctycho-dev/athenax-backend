from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.api.dependencies.auth import get_optional_user
from app.domain.user.model import User
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ClientWithEmail


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_users():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            pg_insert(User)
            .values([
                {"id": 20, "name": "Admin User", "email": "admin_bc@test.com", "password_hash": "x", "role": UserRole.ADMIN, "verified": True},
                {"id": 21, "name": "Regular User", "email": "regular_bc@test.com", "password_hash": "x", "role": UserRole.USER, "verified": True},
            ])
            .on_conflict_do_nothing()
        )
        await session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
        await session.commit()
    await engine.dispose()


def build_mock_user(role: UserRole, user_id: int = 20) -> UserOutSchema:
    return UserOutSchema(
        id=user_id,
        name="Admin User" if role == UserRole.ADMIN else "Regular User",
        email=f"user{user_id}@example.com",
        role=role,
        verified=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


BROADCAST_PAYLOAD = {
    "title": "Test Broadcast",
    "broadcastType": "livestream",
    "status": "draft",
    "tags": [],
}


def _override_admin():
    class _ctx:
        def __enter__(self):
            original = app.dependency_overrides.get(get_current_user)
            self._original = original
            app.dependency_overrides[get_current_user] = lambda: build_mock_user(UserRole.ADMIN, user_id=20)
            return self

        def __exit__(self, *_):
            if self._original is None:
                app.dependency_overrides.pop(get_current_user, None)
            else:
                app.dependency_overrides[get_current_user] = self._original

    return _ctx()


@pytest.mark.asyncio
class TestBroadcastAPI:

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    _counter = 0

    async def _create_broadcast_as_admin(self, client: ClientWithEmail, payload: dict | None = None) -> dict:
        TestBroadcastAPI._counter += 1
        base = {**(payload or BROADCAST_PAYLOAD), "title": f"Test Broadcast {TestBroadcastAPI._counter}"}
        with _override_admin():
            resp = await client.post("/api/v1/broadcast", json=base)
        assert resp.status_code == 201
        return resp.json()

    async def _publish_broadcast(self, client: ClientWithEmail, broadcast_id: int) -> dict:
        with _override_admin():
            resp = await client.patch(f"/api/v1/broadcast/{broadcast_id}", json={"status": "published"})
        assert resp.status_code == 200
        return resp.json()

    # ------------------------------------------------------------------
    # Create — RBAC
    # ------------------------------------------------------------------

    async def test_create_broadcast_forbidden_for_regular_user(self, client: ClientWithEmail):
        response = await client.post("/api/v1/broadcast", json=BROADCAST_PAYLOAD)
        assert response.status_code == 403

    async def test_create_broadcast_success_for_admin(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Broadcast Create Success"}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Broadcast Create Success"
        assert data["slug"] != ""
        assert data["broadcastType"] == "livestream"
        assert data["status"] == "draft"
        assert data["creatorName"] == "Admin User"

    async def test_create_broadcast_generates_slug(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Unique Slug For Broadcast"}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        assert "unique-slug-for-broadcast" in response.json()["slug"]

    async def test_create_broadcast_validation_missing_type(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json={"title": "No Type"})
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # Create — published_at logic
    # ------------------------------------------------------------------

    async def test_create_draft_has_no_published_at(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Broadcast Draft No Published At"}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is None

    async def test_create_published_auto_sets_published_at(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Broadcast Auto Published At", "status": "published"}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None

    async def test_create_with_custom_published_at(self, client: ClientWithEmail):
        custom_date = "2025-03-10T12:00:00+00:00"
        payload = {**BROADCAST_PAYLOAD, "title": "Broadcast Custom Published At", "status": "published", "publishedAt": custom_date}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        assert "2025-03-10" in response.json()["publishedAt"]

    # ------------------------------------------------------------------
    # Create — tags
    # ------------------------------------------------------------------

    async def test_create_broadcast_with_tags(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Broadcast With Tags", "tags": ["fintech", "ai"]}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        tags = response.json()["tags"]
        assert "fintech" in tags
        assert "ai" in tags

    async def test_create_broadcast_tags_trimmed_and_deduped(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Tag Trim Test Broadcast", "tags": ["  BioTech  ", "NanoTech"]}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        tags_lower = [t.lower() for t in response.json()["tags"]]
        assert "biotech" in tags_lower
        assert "nanotech" in tags_lower

    async def test_create_broadcast_duplicate_tags_deduplicated(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Dedup Broadcast Tags", "tags": ["science", "science", "Science"]}
        with _override_admin():
            response = await client.post("/api/v1/broadcast", json=payload)

        assert response.status_code == 201
        tags = response.json()["tags"]
        assert tags.count("science") == 1

    # ------------------------------------------------------------------
    # List — visibility
    # ------------------------------------------------------------------

    async def test_list_broadcasts_is_public(self, client: ClientWithEmail):
        response = await client.get("/api/v1/broadcast")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    async def test_list_broadcasts_only_shows_published_to_public(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/broadcast")
        finally:
            del app.dependency_overrides[get_optional_user]

        ids = [b["id"] for b in response.json()["items"]]
        assert draft["id"] not in ids

    async def test_list_broadcasts_admin_can_filter_by_status(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get("/api/v1/broadcast?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()["items"]]
        assert draft["id"] in ids

    async def test_list_broadcasts_non_admin_status_param_ignored(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/broadcast?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()["items"]]
        assert draft["id"] not in ids
        assert all(b["status"] == "published" for b in response.json()["items"])

    async def test_list_broadcasts_filter_by_type(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "broadcastType": "roundtable", "title": "Roundtable Broadcast", "status": "published"}
        with _override_admin():
            resp = await client.post("/api/v1/broadcast", json=payload)
        assert resp.status_code == 201

        response = await client.get("/api/v1/broadcast?broadcastType=roundtable")
        assert response.status_code == 200
        assert all(b["broadcastType"] == "roundtable" for b in response.json()["items"])

    async def test_list_broadcasts_filter_by_tag(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Tagged Broadcast", "status": "published", "tags": ["quantum-computing"]}
        tagged = await self._create_broadcast_as_admin(client, payload)

        untagged = await self._create_broadcast_as_admin(
            client, {**BROADCAST_PAYLOAD, "title": "Untagged Broadcast", "status": "published"}
        )

        response = await client.get("/api/v1/broadcast?tag=quantum-computing")
        assert response.status_code == 200
        ids = [b["id"] for b in response.json()["items"]]
        assert tagged["id"] in ids
        assert untagged["id"] not in ids

    async def test_list_broadcasts_filter_tag_no_matches(self, client: ClientWithEmail):
        response = await client.get("/api/v1/broadcast?tag=nonexistent-xyz-tag")
        assert response.status_code == 200
        assert response.json()["items"] == []

    # ------------------------------------------------------------------
    # Get by ID
    # ------------------------------------------------------------------

    async def test_get_broadcast_not_found(self, client: ClientWithEmail):
        response = await client.get("/api/v1/broadcast/999999")
        assert response.status_code == 404

    async def test_get_draft_broadcast_hidden_from_public(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/broadcast/{draft['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    async def test_get_draft_broadcast_visible_to_admin(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/broadcast/{draft['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        assert response.json()["id"] == draft["id"]

    async def test_get_published_broadcast_is_public(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        await self._publish_broadcast(client, broadcast["id"])

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/broadcast/{broadcast['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Get by slug
    # ------------------------------------------------------------------

    async def test_get_broadcast_by_slug(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        await self._publish_broadcast(client, broadcast["id"])

        response = await client.get(f"/api/v1/broadcast/slug/{broadcast['slug']}")
        assert response.status_code == 200
        assert response.json()["id"] == broadcast["id"]

    async def test_get_broadcast_by_invalid_slug_returns_404(self, client: ClientWithEmail):
        response = await client.get("/api/v1/broadcast/slug/does-not-exist-ever")
        assert response.status_code == 404

    async def test_get_draft_by_slug_hidden_from_public(self, client: ClientWithEmail):
        draft = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/broadcast/slug/{draft['slug']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def test_update_broadcast_forbidden_for_regular_user(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        response = await client.patch(f"/api/v1/broadcast/{broadcast['id']}", json={"title": "Hacked"})
        assert response.status_code == 403

    async def test_admin_can_update_broadcast(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"description": "Updated description"}
            )

        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"

    async def test_update_title_regenerates_slug(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        original_slug = broadcast["slug"]

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"title": "Brand New Broadcast Title Here"}
            )

        assert response.status_code == 200
        new_slug = response.json()["slug"]
        assert new_slug != original_slug
        assert "brand-new-broadcast-title-here" in new_slug

    async def test_update_status_to_published_sets_published_at(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        assert broadcast["publishedAt"] is None

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"status": "published"}
            )

        assert response.status_code == 200
        assert response.json()["publishedAt"] is not None

    async def test_update_status_to_draft_clears_published_at(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        await self._publish_broadcast(client, broadcast["id"])

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"status": "draft"}
            )

        assert response.status_code == 200
        assert response.json()["publishedAt"] is None

    async def test_update_tags_syncs_correctly(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"tags": ["blockchain"]}
            )

        assert response.status_code == 200
        assert "blockchain" in response.json()["tags"]

    async def test_update_tags_replaces_previous_tags(self, client: ClientWithEmail):
        payload = {**BROADCAST_PAYLOAD, "title": "Tag Replace Broadcast", "tags": ["old-tag"]}
        broadcast = await self._create_broadcast_as_admin(client, payload)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/broadcast/{broadcast['id']}", json={"tags": ["new-tag"]}
            )

        assert response.status_code == 200
        tags = response.json()["tags"]
        assert "new-tag" in tags
        assert "old-tag" not in tags

    async def test_update_nonexistent_broadcast_returns_404(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.patch("/api/v1/broadcast/999999", json={"title": "Ghost"})
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def test_delete_broadcast_forbidden_for_regular_user(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        response = await client.delete(f"/api/v1/broadcast/{broadcast['id']}")
        assert response.status_code == 403

    async def test_admin_can_delete_broadcast(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)

        with _override_admin():
            response = await client.delete(f"/api/v1/broadcast/{broadcast['id']}")

        assert response.status_code == 204

    async def test_delete_nonexistent_broadcast_returns_404(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.delete("/api/v1/broadcast/999999")
        assert response.status_code == 404

    async def test_broadcast_not_found_after_deletion(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)
        broadcast_id = broadcast["id"]

        with _override_admin():
            await client.delete(f"/api/v1/broadcast/{broadcast_id}")

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/broadcast/{broadcast_id}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Schema / response shape
    # ------------------------------------------------------------------

    async def test_broadcast_response_includes_expected_fields(self, client: ClientWithEmail):
        broadcast = await self._create_broadcast_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/broadcast/{broadcast['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        data = response.json()
        for field in ("id", "title", "slug", "broadcastType", "status", "embedUrl",
                      "description", "thumbnailUrl", "originDate", "publishedAt",
                      "creatorName", "tags", "createdAt", "updatedAt"):
            assert field in data, f"Missing field: {field}"
