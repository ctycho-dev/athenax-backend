from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.api.dependencies.auth import get_optional_user
from app.domain.category.model import Category
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
                {"id": 10, "name": "Admin User", "email": "admin@test.com", "password_hash": "x", "role": UserRole.ADMIN, "verified": True},
                {"id": 11, "name": "Regular User", "email": "regular@test.com", "password_hash": "x", "role": UserRole.USER, "verified": True},
            ])
            .on_conflict_do_nothing()
        )
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
    "categoryIds": [],
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

    async def _create_article_as_admin(self, client: ClientWithEmail, payload: dict | None = None) -> dict:
        with _override_admin():
            resp = await client.post("/api/v1/article", json=payload or ARTICLE_PAYLOAD)
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
        assert isinstance(response.json(), list)

    async def test_list_articles_only_shows_published_to_public(self, client: ClientWithEmail):
        # Create a draft (not visible to public)
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/article")
        finally:
            del app.dependency_overrides[get_optional_user]

        ids = [a["id"] for a in response.json()]
        assert draft["id"] not in ids

    async def test_list_articles_admin_can_filter_by_status(self, client: ClientWithEmail):
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get("/api/v1/article?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [a["id"] for a in response.json()]
        assert draft["id"] in ids

    async def test_list_articles_filter_by_type(self, client: ClientWithEmail):
        roundtable_payload = {**ARTICLE_PAYLOAD, "articleType": "roundtable", "title": "Roundtable Article", "status": "published"}
        with _override_admin():
            resp = await client.post("/api/v1/article", json=roundtable_payload)
        assert resp.status_code == 201

        response = await client.get("/api/v1/article?articleType=roundtable")
        assert response.status_code == 200
        assert all(a["articleType"] == "roundtable" for a in response.json())

    async def test_list_articles_filter_by_type_livestream(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "articleType": "livestream", "title": "Livestream One", "status": "published"}
        with _override_admin():
            resp = await client.post("/api/v1/article", json=payload)
        assert resp.status_code == 201

        response = await client.get("/api/v1/article?articleType=livestream")
        assert response.status_code == 200
        assert all(a["articleType"] == "livestream" for a in response.json())

    async def test_list_articles_non_admin_status_draft_param_ignored(self, client: ClientWithEmail):
        # Non-admin passing ?status=draft should still only get published
        draft = await self._create_article_as_admin(client)

        app.dependency_overrides[get_optional_user] = lambda: None
        try:
            response = await client.get("/api/v1/article?status=draft")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        ids = [a["id"] for a in response.json()]
        assert draft["id"] not in ids
        assert all(a["status"] == "published" for a in response.json())

    async def test_list_articles_admin_filter_by_published_status(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        await self._publish_article(client, article["id"])

        app.dependency_overrides[get_optional_user] = lambda: build_mock_user(UserRole.ADMIN)
        try:
            response = await client.get("/api/v1/article?status=published")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        assert all(a["status"] == "published" for a in response.json())

    async def test_list_articles_filter_by_category_id(self, client: ClientWithEmail, db_session):
        result = await db_session.execute(
            insert(Category).values(name="Filter Category", parent_id=None).returning(Category.id)
        )
        category_id = result.scalar_one()
        await db_session.commit()

        # Article with the category
        payload = {**ARTICLE_PAYLOAD, "title": "Categorised Article", "status": "published", "categoryIds": [category_id]}
        tagged = await self._create_article_as_admin(client, payload)

        # Article without the category
        untagged = await self._create_article_as_admin(
            client, {**ARTICLE_PAYLOAD, "title": "Uncategorised Article", "status": "published"}
        )

        response = await client.get(f"/api/v1/article?categoryId={category_id}")
        assert response.status_code == 200
        ids = [a["id"] for a in response.json()]
        assert tagged["id"] in ids
        assert untagged["id"] not in ids

    async def test_list_articles_filter_by_category_id_no_matches(self, client: ClientWithEmail, db_session):
        result = await db_session.execute(
            insert(Category).values(name="Empty Category", parent_id=None).returning(Category.id)
        )
        category_id = result.scalar_one()
        await db_session.commit()

        response = await client.get(f"/api/v1/article?categoryId={category_id}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_articles_filter_combined_type_and_category(self, client: ClientWithEmail, db_session):
        result = await db_session.execute(
            insert(Category).values(name="Combined Filter Cat", parent_id=None).returning(Category.id)
        )
        category_id = result.scalar_one()
        await db_session.commit()

        # whitepaper in category
        wp_payload = {**ARTICLE_PAYLOAD, "articleType": "whitepaper", "title": "WP in Category", "status": "published", "categoryIds": [category_id]}
        match = await self._create_article_as_admin(client, wp_payload)

        # roundtable in same category — should NOT appear in whitepaper filter
        other_payload = {**ARTICLE_PAYLOAD, "articleType": "roundtable", "title": "Roundtable in Category", "status": "published", "categoryIds": [category_id]}
        await self._create_article_as_admin(client, other_payload)

        response = await client.get(f"/api/v1/article?articleType=whitepaper&categoryId={category_id}")
        assert response.status_code == 200
        ids = [a["id"] for a in response.json()]
        assert match["id"] in ids
        assert all(a["articleType"] == "whitepaper" for a in response.json())

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
        with _override_admin():
            response = await client.post("/api/v1/article", json=ARTICLE_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == ARTICLE_PAYLOAD["title"]
        assert data["slug"] != ""
        assert data["articleType"] == "whitepaper"
        assert data["status"] == "draft"
        assert data["createdById"] == 10
        assert data["creatorName"] == "Admin User"

    async def test_create_article_generates_slug(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "title": "Unique Slug Generation Test"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert "unique-slug-generation-test" in response.json()["slug"]

    # ------------------------------------------------------------------
    # Create — published_at logic
    # ------------------------------------------------------------------

    async def test_create_draft_has_no_published_at(self, client: ClientWithEmail):
        with _override_admin():
            response = await client.post("/api/v1/article", json=ARTICLE_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is None

    async def test_create_published_auto_sets_published_at(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "status": "published"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None

    async def test_create_with_custom_published_at(self, client: ClientWithEmail):
        custom_date = "2025-01-15T10:00:00+00:00"
        payload = {**ARTICLE_PAYLOAD, "status": "published", "publishedAt": custom_date}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["publishedAt"] is not None
        # The date in the response should correspond to the custom date
        assert "2025-01-15" in response.json()["publishedAt"]

    # ------------------------------------------------------------------
    # Create — categories
    # ------------------------------------------------------------------

    async def test_create_article_with_parent_category(self, client: ClientWithEmail, db_session):
        result = await db_session.execute(
            insert(Category).values(name="Tech", parent_id=None).returning(Category.id)
        )
        category_id = result.scalar_one()
        await db_session.commit()

        payload = {**ARTICLE_PAYLOAD, "categoryIds": [category_id]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert "Tech" in response.json()["categories"]

    async def test_create_article_with_invalid_category_returns_404(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "categoryIds": [999999]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 404

    async def test_create_article_with_subcategory_returns_400(self, client: ClientWithEmail, db_session):
        parent_result = await db_session.execute(
            insert(Category).values(name="Science", parent_id=None).returning(Category.id)
        )
        parent_id = parent_result.scalar_one()
        child_result = await db_session.execute(
            insert(Category).values(name="Physics", parent_id=parent_id).returning(Category.id)
        )
        child_id = child_result.scalar_one()
        await db_session.commit()

        payload = {**ARTICLE_PAYLOAD, "categoryIds": [child_id]}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 400

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

    async def test_update_title_regenerates_slug(self, client: ClientWithEmail):
        article = await self._create_article_as_admin(client)
        original_slug = article["slug"]

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"title": "Completely New Title Here"}
            )

        assert response.status_code == 200
        new_slug = response.json()["slug"]
        assert new_slug != original_slug
        assert "completely-new-title-here" in new_slug

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

    async def test_update_categories_syncs_correctly(self, client: ClientWithEmail, db_session):
        cat_result = await db_session.execute(
            insert(Category).values(name="Finance", parent_id=None).returning(Category.id)
        )
        cat_id = cat_result.scalar_one()
        await db_session.commit()

        article = await self._create_article_as_admin(client)

        with _override_admin():
            response = await client.patch(
                f"/api/v1/article/{article['id']}", json={"categoryIds": [cat_id]}
            )

        assert response.status_code == 200
        assert "Finance" in response.json()["categories"]

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
                      "creatorName", "categories", "createdAt", "updatedAt", "createdById"):
            assert field in data, f"Missing field: {field}"

    async def test_article_type_livestream(self, client: ClientWithEmail):
        payload = {**ARTICLE_PAYLOAD, "articleType": "livestream", "title": "Livestream Article"}
        with _override_admin():
            response = await client.post("/api/v1/article", json=payload)

        assert response.status_code == 201
        assert response.json()["articleType"] == "livestream"
