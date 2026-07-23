import re
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.api.dependencies.auth import get_optional_user
from app.domain.broadcast.model import Broadcast
from app.domain.user.model import User
from app.domain.user.schema import UserOutSchema
from app.enums.enums import BroadcastStatus, BroadcastType, UserRole
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ClientWithEmail

SEED_BROADCAST_ID = 10


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_users():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            pg_insert(User)
            .values([
                {"id": 10, "name": "Admin User", "email": "admin@test.com", "password_hash": "x", "role": UserRole.ADMIN, "verified": True},
                {"id": 11, "name": "Regular User", "email": "regular@test.com", "password_hash": "x", "role": UserRole.USER, "verified": True},
            ])
            .on_conflict_do_nothing()
        )
        await session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
        await session.execute(
            pg_insert(Broadcast)
            .values([{
                "id": SEED_BROADCAST_ID,
                "title": "Seed Broadcast",
                "slug": "seed-broadcast",
                "broadcast_type": BroadcastType.LIVESTREAM,
                "status": BroadcastStatus.PUBLISHED,
            }])
            .on_conflict_do_nothing()
        )
        await session.execute(text("SELECT setval('broadcasts_id_seq', (SELECT MAX(id) FROM broadcasts))"))
        await session.commit()
    await engine.dispose()


def build_mock_user(role: UserRole, user_id: int = 10) -> UserOutSchema:
    return UserOutSchema(
        id=user_id,
        name="Admin User" if role == UserRole.ADMIN else "Regular User",
        email=f"user{user_id}@example.com",
        role=role,
        verified=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


ARTICLE_PAYLOAD = {
    "title": "Test Article Title",
    "articleType": "whitepaper",
    "content": "# Hello\n\nThis is the body.",
    "status": "draft",
    "tags": [],
}


def _override_admin():
    """Context manager that swaps get_current_user to an admin."""
    class _ctx:
        def __enter__(self):
            original = app.dependency_overrides[get_current_user]
            self._original = original
            app.dependency_overrides[get_current_user] = lambda: build_mock_user(UserRole.ADMIN, user_id=10)
            return self

        def __exit__(self, *_):
            app.dependency_overrides[get_current_user] = self._original

    return _ctx()


@pytest.mark.asyncio
class TestArticleAPI:

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    _counter = 0

    async def _create_article_as_admin(self, client: ClientWithEmail, payload: dict | None = None) -> dict:
        TestArticleAPI._counter += 1
        base = {**(payload or ARTICLE_PAYLOAD), "title": f"Test Article {TestArticleAPI._counter}"}
        with _override_admin():
            resp = await client.post("/api/v1/article", json=base)
        assert resp.status_code == 201
        return resp.json()

    async def _publish_article(self, client: ClientWithEmail, article_id: int) -> dict:
        with _override_admin():
            resp = await client.patch(f"/api/v1/article/{article_id}", json={"status": "published"})
        assert resp.status_code == 200
        return resp.json()

    # ------------------------------------------------------------------
    # List — public visibility
    # ------------------------------------------------------------------

    async def test_list_articles_is_public(self, client: ClientWithEmail):
        response = await client.get("/api/v1/article")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    async def test_list_articles_only_shows_published_to_public(self, client: ClientWithEmail):
        # Create a draft (not visible to public)
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/article")
        finally:
            del app.dependency_overrides[get_optional_user]

        ids = [a["id"] for a in response.json()["items"]]
        assert draft["id"] not in ids

    async def test_list_articles_admin_can_filter_by_status(self, client: ClientWithEmail):
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get("/api/v1/article?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [a["id"] for a in response.json()["items"]]
        assert draft["id"] in ids

    async def test_list_articles_filter_by_type(self, client: ClientWithEmail):
        roundtable_payload = {**ARTICLE_PAYLOAD, "articleType": "roundtable", "title": "Roundtable Article", "status": "published"}
        with _override_admin():
            resp = await client.post("/api/v1/article", json=roundtable_payload)
        assert resp.status_code == 201

        response = await client.get("/api/v1/article?articleType=roundtable")
        assert response.status_code == 200
        assert all(a["articleType"] == "roundtable" for a in response.json()["items"])

    async def test_list_articles_filter_by_type_livestream(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "articleType": "livestream", "title": "Livestream One", "status": "published"}
        with _override_admin():
            resp = await client.post("/api/v1/article", json=payload)
        assert resp.status_code == 201

        response = await client.get("/api/v1/article?articleType=livestream")
        assert response.status_code == 200
        assert all(a["articleType"] == "livestream" for a in response.json()["items"])

    async def test_list_articles_non_admin_status_draft_param_ignored(self, client: ClientWithEmail):
        # Non-admin passing ?status=draft should still only get published
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/article?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [a["id"] for a in response.json()["items"]]
        assert draft["id"] not in ids
        assert all(a["status"] == "published" for a in response.json()["items"])

    async def test_list_articles_admin_filter_by_published_status(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        await self._publish_article(client, article["id"])

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get("/api/v1/article?status=published")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        assert all(a["status"] == "published" for a in response.json()["items"])

    async def test_list_articles_filter_by_tag(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Tagged Article", "status": "published", "tags": ["machine-learning"]}
        tagged = await self._create_article_as_admin(client, payload)

        untagged = await self._create_article_as_admin(
            client, {**ARTICLE_PAYLOAD, "title": "Untagged Article", "status": "published"}
        )

        response = await client.get("/api/v1/article?tag=machine-learning")
        assert response.status_code == 200
        ids = [a["id"] for a in response.json()["items"]]
        assert tagged["id"] in ids
        assert untagged["id"] not in ids

    async def test_list_articles_filter_by_tag_no_matches(self, client: ClientWithEmail):
        response = await client.get("/api/v1/article?tag=nonexistent-tag-xyz")
        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_list_articles_filter_combined_type_and_tag(self, client: ClientWithEmail):
        tag = "combined-filter-tag"

        wp_payload = {**ARTICLE_PAYLOAD, "articleType": "whitepaper", "title": "WP with Tag", "status": "published", "tags": [tag]}
        match = await self._create_article_as_admin(client, wp_payload)

        other_payload = {**ARTICLE_PAYLOAD, "articleType": "roundtable", "title": "Roundtable with Tag", "status": "published", "tags": [tag]}
        await self._create_article_as_admin(client, other_payload)

        response = await client.get(f"/api/v1/article?articleType=whitepaper&tag={tag}")
        assert response.status_code == 200
        ids = [a["id"] for a in response.json()["items"]]
        assert match["id"] in ids
        assert all(a["articleType"] == "whitepaper" for a in response.json()["items"])

    # ------------------------------------------------------------------
    # Get by ID
    # ------------------------------------------------------------------

    async def test_get_article_not_found(self, client: ClientWithEmail):
        response = await client.get("/api/v1/article/999999")
        assert response.status_code == 404

    async def test_get_draft_article_hidden_from_public(self, client: ClientWithEmail):
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/article/{draft['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    async def test_get_draft_article_visible_to_admin(self, client: ClientWithEmail):
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/article/{draft['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        assert response.json()["id"] == draft["id"]

    async def test_get_published_article_is_public(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        await self._publish_article(client, article["id"])

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/article/{article['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Get by slug
    # ------------------------------------------------------------------

    async def test_get_article_by_slug(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        await self._publish_article(client, article["id"])

        response = await client.get(f"/api/v1/article/slug/{article['slug']}")
        assert response.status_code == 200
        assert response.json()["id"] == article["id"]

    async def test_get_article_by_invalid_slug_returns_404(self, client: ClientWithEmail):
        response = await client.get("/api/v1/article/slug/does-not-exist-ever")
        assert response.status_code == 404

    async def test_get_draft_by_slug_hidden_from_public(self, client: ClientWithEmail):
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get(f"/api/v1/article/slug/{draft['slug']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Create — RBAC
    # ------------------------------------------------------------------

    async def test_create_article_forbidden_for_regular_user(self, client: ClientWithEmail):
        response = await client.post("/api/v1/article", json=ARTICLE_PAYLOAD)
        assert response.status_code == 403

    async def test_create_article_success_for_admin(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Article Create Success"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Article Create Success"
        assert data["slug"] != ""
        assert data["articleType"] == "whitepaper"
        assert data["status"] == "draft"
        assert data["creatorName"] == "Admin User"

    async def test_create_article_generates_slug(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Unique Slug Generation Test"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert "unique-slug-generation-test" in response.json()["slug"]

    async def test_create_article_duplicate_title_gets_unique_slug(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Article Slug Collision Subject"}
        with _override_admin():
            first = await client.post("/api/v1/article", json=payload)
            second = await client.post("/api/v1/article", json=payload)

        assert first.status_code == 201
        assert second.status_code == 201
        # First gets the clean slug; the collision falls back to a random 4-hex suffix.
        assert first.json()["slug"] == "article-slug-collision-subject"
        assert re.fullmatch(r"article-slug-collision-subject-[0-9a-f]{4}", second.json()["slug"])

    # ------------------------------------------------------------------
    # Create — published_at logic
    # ------------------------------------------------------------------

    async def test_create_draft_has_no_published_at(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Article Draft No Published At"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is None

    async def test_create_published_auto_sets_published_at(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Article Auto Published At", "status": "published"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None

    async def test_create_with_custom_published_at(self, client: ClientWithEmail):
        custom_date = "2025-01-15T10:00:00+00:00"
        payload = {**ARTICLE_PAYLOAD, "title": "Article Custom Published At", "status": "published", "publishedAt": custom_date}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None
        assert "2025-01-15" in response.json()["publishedAt"]

    async def test_create_draft_keeps_custom_published_at(self, client: ClientWithEmail):
        # A chosen date must survive being saved as a draft, not be wiped.
        custom_date = "2025-01-15T10:00:00+00:00"
        payload = {**ARTICLE_PAYLOAD, "title": "Draft Custom Published At", "status": "draft", "publishedAt": custom_date}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert "2025-01-15" in response.json()["publishedAt"]

    # ------------------------------------------------------------------
    # Create — tags
    # ------------------------------------------------------------------

    async def test_create_article_with_tags(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Article With Tags", "tags": ["biotech", "ai"]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        tags = response.json()["tags"]
        assert "biotech" in tags
        assert "ai" in tags

    async def test_create_article_tags_trimmed_and_deduped(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Tag Case Test", "tags": ["MachineLearning", "  BioTech  "]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        tags = response.json()["tags"]
        tags_lower = [t.lower() for t in tags]
        assert "machinelearning" in tags_lower
        assert "biotech" in tags_lower

    async def test_create_article_duplicate_tags_deduplicated(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Dedup Tags Test", "tags": ["science", "science", "Science"]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        tags = response.json()["tags"]
        assert tags.count("science") == 1

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def test_update_article_forbidden_for_regular_user(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        response = await client.patch(f"/api/v1/article/{article['id']}", json={"title": "Hacked"})
        assert response.status_code == 403

    async def test_admin_can_update_article(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"content": "Updated content"}
            )

        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    async def test_update_title_keeps_slug_stable(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        original_slug = article["slug"]

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"title": "Completely New Title Here"}
            )

        assert response.status_code == 200
        assert response.json()["slug"] == original_slug

    async def test_update_explicit_slug_changes_slug(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        original_slug = article["slug"]

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"slug": "brand-new-slug"}
            )

        assert response.status_code == 200
        assert response.json()["slug"] == "brand-new-slug"
        assert response.json()["slug"] != original_slug

    async def test_update_slug_collision_gets_random_suffix(self, client: ClientWithEmail):
        first = await self._create_article_as_admin(client)
        second = await self._create_article_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{second['id']}", json={"slug": first["slug"]}
            )

        assert response.status_code == 200
        new_slug = response.json()["slug"]
        assert new_slug != first["slug"]
        assert re.fullmatch(rf"{re.escape(first['slug'])}-[0-9a-f]{{4}}", new_slug)

    async def test_update_status_to_published_sets_published_at(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        assert article["publishedAt"] is None

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"status": "published"}
            )

        assert response.status_code == 200
        assert response.json()["publishedAt"] is not None

    async def test_update_status_to_draft_clears_published_at(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        await self._publish_article(client, article["id"])

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"status": "draft"}
            )

        assert response.status_code == 200
        assert response.json()["publishedAt"] is None

    async def test_publish_preserves_existing_published_at(self, client: ClientWithEmail):
        # Publishing a draft that already has a chosen date must not reset it to now.
        custom_date = "2025-01-15T10:00:00+00:00"
        article = await self._create_article_as_admin(
            client, payload={**ARTICLE_PAYLOAD, "status": "draft", "publishedAt": custom_date}
        )
        assert "2025-01-15" in article["publishedAt"]

        published = await self._publish_article(client, article["id"])
        assert "2025-01-15" in published["publishedAt"]

    async def test_update_tags_syncs_correctly(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"tags": ["finance"]}
            )

        assert response.status_code == 200
        assert "finance" in response.json()["tags"]

    async def test_update_tags_replaces_previous_tags(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Tag Replace Test", "tags": ["old-tag"]}
        article = await self._create_article_as_admin(client, payload)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"tags": ["new-tag"]}
            )

        assert response.status_code == 200
        tags = response.json()["tags"]
        assert "new-tag" in tags
        assert "old-tag" not in tags

    async def test_update_nonexistent_article_returns_404(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.patch("/api/v1/article/999999", json={"title": "Ghost"})

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def test_delete_article_forbidden_for_regular_user(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        response = await client.delete(f"/api/v1/article/{article['id']}")
        assert response.status_code == 403

    async def test_admin_can_delete_article(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        with _override_admin():
            response = await client.delete(f"/api/v1/article/{article['id']}")

        assert response.status_code == 204

    async def test_delete_nonexistent_article_returns_404(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.delete("/api/v1/article/999999")

        assert response.status_code == 404

    async def test_article_not_found_after_deletion(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        article_id = article["id"]

        with _override_admin():
            await client.delete(f"/api/v1/article/{article_id}")

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/article/{article_id}")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Schema / response shape
    # ------------------------------------------------------------------

    async def test_article_response_includes_expected_fields(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get(f"/api/v1/article/{article['id']}")
        finally:
            del app.dependency_overrides[get_optional_user]

        data = response.json()
        for field in ("id", "title", "slug", "articleType", "content", "status", "publishedAt",
                      "creatorName", "tags", "createdAt", "updatedAt"):
            assert field in data, f"Missing field: {field}"

    async def test_article_type_livestream(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "articleType": "livestream", "title": "Livestream Article"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["articleType"] == "livestream"
