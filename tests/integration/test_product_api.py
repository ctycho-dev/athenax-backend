from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.api.dependencies.auth import get_optional_user
from app.api.dependencies.services import get_storage_service
from app.domain.user.model import User
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ClientWithEmail


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_users():
    """Insert users needed by product FK constraints."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            pg_insert(User)
            .values(
                [
                    {"id": 1, "name": "Founder", "email": "founder@test.com", "password_hash": "x", "role": UserRole.FOUNDER, "verified": True},
                    {"id": 2, "name": "Other", "email": "other@test.com", "password_hash": "x", "role": UserRole.FOUNDER, "verified": True},
                    {"id": 3, "name": "Investor", "email": "investor@test.com", "password_hash": "x", "role": UserRole.INVESTOR, "verified": True},
                    {"id": 99, "name": "Admin", "email": "admin@test.com", "password_hash": "x", "role": UserRole.ADMIN, "verified": True},
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


PRODUCT_PAYLOAD = {
    "name": "My Test Product",
    "sector": "AI & Agents",
    "stage": "Seed",
    "categoryIds": [],
}


@pytest.mark.asyncio
class TestProductAPI:

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    async def test_list_products_is_public(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_unauthorized():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_user] = override_unauthorized
        try:
            response = await client.get("/api/v1/product")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data and "total" in data

    async def test_get_product_not_found(self, client: ClientWithEmail):
        response = await client.get("/api/v1/product/999999")
        assert response.status_code == 404

    async def test_list_comments_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_unauthorized():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_user] = override_unauthorized
        try:
            response = await client.get(f"/api/v1/product/{product_id}/comments")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # ------------------------------------------------------------------
    # RBAC — create
    # ------------------------------------------------------------------

    async def test_create_product_allowed_for_any_authenticated_user(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_regular_user():
            return build_mock_user(UserRole.USER)

        app.dependency_overrides[get_current_user] = override_regular_user
        try:
            payload = {**PRODUCT_PAYLOAD, "name": "Regular User Product"}
            response = await client.post("/api/v1/product", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Regular User Product"

    async def test_create_product_allowed_for_founder(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_founder():
            return build_mock_user(UserRole.FOUNDER)

        app.dependency_overrides[get_current_user] = override_founder
        try:
            payload = {**PRODUCT_PAYLOAD, "name": "Founder Product 1"}
            response = await client.post("/api/v1/product", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Founder Product 1"
        assert data["slug"]
        assert data["createdById"] == 1
        assert data["status"] == "pending"
        assert data["voteCount"] == 0
        assert data["bookmarkCount"] == 0
        assert data["investorInterestCount"] == 0

    async def test_create_product_allowed_for_admin(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            payload = {**PRODUCT_PAYLOAD, "name": "Admin Product 1"}
            response = await client.post("/api/v1/product", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201

    async def test_create_product_same_name_generates_unique_slugs(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_founder():
            return build_mock_user(UserRole.FOUNDER)

        app.dependency_overrides[get_current_user] = override_founder
        try:
            payload = {**PRODUCT_PAYLOAD, "name": "Duplicate Name"}
            response_1 = await client.post("/api/v1/product", json=payload)
            response_2 = await client.post("/api/v1/product", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response_1.status_code == 201
        assert response_2.status_code == 201
        assert response_1.json()["slug"] != response_2.json()["slug"]

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    _slug_counter = 0

    async def _create_product_as_founder(
        self, client: ClientWithEmail, user_id: int = 1, approve: bool = True
    ) -> int:
        TestProductAPI._slug_counter += 1
        original = app.dependency_overrides[get_current_user]

        async def override():
            return build_mock_user(UserRole.FOUNDER, user_id=user_id)

        app.dependency_overrides[get_current_user] = override
        try:
            payload = {**PRODUCT_PAYLOAD, "name": f"Product {TestProductAPI._slug_counter}"}
            resp = await client.post("/api/v1/product", json=payload)
        finally:
            app.dependency_overrides[get_current_user] = original

        assert resp.status_code == 201
        product_id = resp.json()["id"]

        if approve:
            async def override_admin():
                return build_mock_user(UserRole.ADMIN, user_id=99)

            app.dependency_overrides[get_current_user] = override_admin
            try:
                verify_resp = await client.patch(
                    f"/api/v1/product/{product_id}/status", json={"status": "approved"}
                )
            finally:
                app.dependency_overrides[get_current_user] = original
            assert verify_resp.status_code == 200

        return product_id

    # ------------------------------------------------------------------
    # Ownership / RBAC — update
    # ------------------------------------------------------------------

    async def test_owner_can_update_own_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}", json={"name": "Updated Name"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_non_owner_founder_cannot_update_others_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.FOUNDER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}", json={"name": "Hijacked"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_admin_can_update_any_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}", json={"name": "Admin updated"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["name"] == "Admin updated"

    async def test_update_product_not_found(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch("/api/v1/product/999999", json={"name": "X"})
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Ownership / RBAC — delete
    # ------------------------------------------------------------------

    async def test_owner_can_delete_own_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.delete(f"/api/v1/product/{product_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    async def test_non_owner_founder_cannot_delete_others_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.FOUNDER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.delete(f"/api/v1/product/{product_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Votes
    # ------------------------------------------------------------------

    async def test_vote_adds_and_removes_vote(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        response = await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": True})
        assert response.status_code == 200
        assert response.json()["count"] == 1

        response = await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": False})
        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_duplicate_vote_is_idempotent(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": True})
        response = await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": True})
        assert response.status_code == 200
        assert response.json()["count"] == 1

    async def test_vote_count_reflected_in_product_response(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": True})
        response = await client.get(f"/api/v1/product/{product_id}")

        assert response.status_code == 200
        assert response.json()["voteCount"] == 1

    async def test_vote_on_missing_product_returns_404(self, client: ClientWithEmail):
        response = await client.put("/api/v1/product/999999/vote", json={"voted": True})
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Bookmarks
    # ------------------------------------------------------------------

    async def test_bookmark_adds_and_removes(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        response = await client.put(f"/api/v1/product/{product_id}/bookmark", json={"bookmarked": True})
        assert response.status_code == 200
        assert response.json()["count"] == 1

        response = await client.put(f"/api/v1/product/{product_id}/bookmark", json={"bookmarked": False})
        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_duplicate_bookmark_is_idempotent(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        await client.put(f"/api/v1/product/{product_id}/bookmark", json={"bookmarked": True})
        response = await client.put(f"/api/v1/product/{product_id}/bookmark", json={"bookmarked": True})
        assert response.status_code == 200
        assert response.json()["count"] == 1

    async def test_bookmark_count_reflected_in_product_response(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        await client.put(f"/api/v1/product/{product_id}/bookmark", json={"bookmarked": True})
        response = await client.get(f"/api/v1/product/{product_id}")

        assert response.status_code == 200
        assert response.json()["bookmarkCount"] == 1

    # ------------------------------------------------------------------
    # Investor Interest
    # ------------------------------------------------------------------

    async def test_investor_interest_forbidden_for_non_investor(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.put(f"/api/v1/product/{product_id}/interest", json={"interested": True})
        assert response.status_code == 403
        assert response.json()["detail"] == "Investor role required"

    async def test_investor_interest_allowed_for_investor(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_investor():
            return build_mock_user(UserRole.INVESTOR, user_id=3)

        app.dependency_overrides[get_current_user] = override_investor
        try:
            response = await client.put(
                f"/api/v1/product/{product_id}/interest", json={"interested": True}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["count"] == 1

    async def test_investor_interest_removes(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_investor():
            return build_mock_user(UserRole.INVESTOR, user_id=3)

        app.dependency_overrides[get_current_user] = override_investor
        try:
            await client.put(f"/api/v1/product/{product_id}/interest", json={"interested": True})
            response = await client.put(
                f"/api/v1/product/{product_id}/interest", json={"interested": False}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_investor_interest_count_reflected_in_product_response(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_investor():
            return build_mock_user(UserRole.INVESTOR, user_id=3)

        app.dependency_overrides[get_current_user] = override_investor
        try:
            await client.put(f"/api/v1/product/{product_id}/interest", json={"interested": True})
        finally:
            app.dependency_overrides[get_current_user] = original

        response = await client.get(f"/api/v1/product/{product_id}")
        assert response.status_code == 200
        assert response.json()["investorInterestCount"] == 1

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def test_create_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)

        response = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Great product!"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "Great product!"
        assert data["productId"] == product_id
        assert data["createdById"] == 1

    async def test_list_comments(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        await client.post(f"/api/v1/product/{product_id}/comments", json={"text": "Comment 1"})
        await client.post(f"/api/v1/product/{product_id}/comments", json={"text": "Comment 2"})

        response = await client.get(f"/api/v1/product/{product_id}/comments")
        assert response.status_code == 200
        comments = response.json()
        assert len(comments) >= 2

    async def test_owner_can_update_own_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Original"}
        )
        comment_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/product/{product_id}/comments/{comment_id}",
            json={"text": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Updated"

    async def test_non_owner_cannot_update_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Owner comment"}
        )
        comment_id = create_resp.json()["id"]

        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.USER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/comments/{comment_id}",
                json={"text": "Hijacked"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_owner_can_delete_own_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "To delete"}
        )
        comment_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/product/{product_id}/comments/{comment_id}"
        )
        assert response.status_code == 204

    async def test_non_owner_cannot_delete_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Owner comment"}
        )
        comment_id = create_resp.json()["id"]

        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.USER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.delete(
                f"/api/v1/product/{product_id}/comments/{comment_id}"
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_comment_on_missing_product_returns_404(self, client: ClientWithEmail):
        response = await client.post(
            "/api/v1/product/999999/comments", json={"text": "Ghost comment"}
        )
        assert response.status_code == 404

    async def test_update_nonexistent_comment_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.patch(
            f"/api/v1/product/{product_id}/comments/999999",
            json={"text": "X"},
        )
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    async def test_newly_created_product_has_pending_status(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_optional_user] = override_admin
        try:
            response = await client.get("/api/v1/product?status=pending")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        data = response.json()
        matching = [p for p in data["items"] if p["id"] == product_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "pending"

    async def test_list_defaults_to_approved_only(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        response = await client.get("/api/v1/product")
        assert response.status_code == 200
        data = response.json()
        ids = [p["id"] for p in data["items"]]
        assert product_id not in ids

    async def test_list_with_status_pending_returns_pending(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_optional_user] = override_admin
        try:
            response = await client.get("/api/v1/product?status=pending")
        finally:
            del app.dependency_overrides[get_optional_user]

        assert response.status_code == 200
        data = response.json()
        ids = [p["id"] for p in data["items"]]
        assert product_id in ids

    async def test_get_pending_product_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        response = await client.get(f"/api/v1/product/{product_id}")
        assert response.status_code == 404

    async def test_admin_can_approve_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/status", json={"status": "approved"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["status"] == "approved"

        # Now visible publicly
        public_response = await client.get(f"/api/v1/product/{product_id}")
        assert public_response.status_code == 200

    async def test_admin_can_reject_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/status", json={"status": "rejected"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    async def test_non_admin_cannot_verify(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        original = app.dependency_overrides[get_current_user]

        async def override_founder():
            return build_mock_user(UserRole.FOUNDER)

        app.dependency_overrides[get_current_user] = override_founder
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/status", json={"status": "approved"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_verify_nonexistent_product_returns_404(self, client: ClientWithEmail):
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                "/api/v1/product/999999/verify", json={"status": "approved"}
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 404

    async def test_vote_on_pending_product_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        response = await client.put(f"/api/v1/product/{product_id}/vote", json={"voted": True})
        assert response.status_code == 404

    async def test_comment_on_pending_product_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        response = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Sneaky comment"}
        )
        assert response.status_code == 404

    async def test_approved_product_visible_in_public_list(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=True)
        response = await client.get("/api/v1/product")
        assert response.status_code == 200
        data = response.json()
        ids = [p["id"] for p in data["items"]]
        assert product_id in ids

    # ------------------------------------------------------------------
    # Comment — pin
    # ------------------------------------------------------------------

    async def test_admin_can_pin_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Pin me"}
        )
        comment_id = create_resp.json()["id"]
        assert create_resp.json()["pinned"] is False

        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/comments/{comment_id}/pin",
                json={"pinned": True},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["pinned"] is True

    async def test_non_admin_cannot_pin_comment(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        create_resp = await client.post(
            f"/api/v1/product/{product_id}/comments", json={"text": "Pin me"}
        )
        comment_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/product/{product_id}/comments/{comment_id}/pin",
            json={"pinned": True},
        )
        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------

    async def test_list_links_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/links")
        assert response.status_code == 200
        assert response.json() == []

    async def test_owner_can_create_link(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "github", "url": "https://github.com/test"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["linkType"] == "github"
        assert data["url"] == "https://github.com/test"
        assert data["productId"] == product_id

    async def test_non_owner_cannot_create_link(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.FOUNDER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "github", "url": "https://github.com/test"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_duplicate_link_type_returns_error(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "github", "url": "https://github.com/first"},
            )
            response = await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "github", "url": "https://github.com/second"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code in (400, 409, 500)

    async def test_owner_can_update_link(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "website", "url": "https://old.com"},
            )
            link_id = create_resp.json()["id"]
            response = await client.patch(
                f"/api/v1/product/{product_id}/links/{link_id}",
                json={"url": "https://new.com"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["url"] == "https://new.com"

    async def test_owner_can_delete_link(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/links",
                json={"linkType": "docs", "url": "https://docs.com"},
            )
            link_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/links/{link_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    async def test_link_not_found_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/links/999999",
                json={"url": "https://x.com"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    async def test_list_media_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/media")
        assert response.status_code == 200
        assert response.json() == []

    async def test_admin_can_create_media(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/media",
                json={"mediaType": "image", "storageKey": "uploads/hero.png", "sortOrder": 0},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["mediaType"] == "image"
        assert data["storageKey"] == "uploads/hero.png"

    async def test_non_admin_cannot_create_media(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/media",
                json={"mediaType": "image", "storageKey": "uploads/other.png", "sortOrder": 0},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_admin_can_update_media_sort_order(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/media",
                json={"mediaType": "image", "storageKey": "uploads/img.png", "sortOrder": 0},
            )
            media_id = create_resp.json()["id"]
            response = await client.patch(
                f"/api/v1/product/{product_id}/media/{media_id}",
                json={"sortOrder": 5},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["sortOrder"] == 5

    async def test_admin_can_delete_media(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/media",
                json={"mediaType": "image", "storageKey": "uploads/del.png", "sortOrder": 0},
            )
            media_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/media/{media_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    # ------------------------------------------------------------------
    # Media upload
    # ------------------------------------------------------------------

    async def test_admin_can_upload_media(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        uploaded: list[dict] = []

        class FakeStorage:
            def build_storage_key(self, product_id: int, filename: str) -> str:
                return f"products/{product_id}/abc_{filename}"

            async def upload_file(self, key: str, data: bytes, content_type: str) -> None:
                uploaded.append({"key": key, "content_type": content_type})

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        app.dependency_overrides[get_storage_service] = lambda: FakeStorage()
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/media/upload",
                files={"file": ("hero.jpg", b"fake-image-bytes", "image/jpeg")},
                data={"sort_order": "10"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original
            app.dependency_overrides.pop(get_storage_service, None)

        assert response.status_code == 201
        data = response.json()
        assert data["storageKey"] == f"products/{product_id}/abc_hero.jpg"
        assert data["sortOrder"] == 10
        assert data["mediaType"] == "image"
        assert len(uploaded) == 1
        assert uploaded[0]["content_type"] == "image/jpeg"

    async def test_non_admin_cannot_upload_media(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_founder():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_founder
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/media/upload",
                files={"file": ("hero.jpg", b"fake-image-bytes", "image/jpeg")},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_upload_media_rejects_unsupported_type(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        class FakeStorage:
            def build_storage_key(self, product_id: int, filename: str) -> str:
                return f"products/{product_id}/abc_{filename}"

            async def upload_file(self, key: str, data: bytes, content_type: str) -> None:
                pass

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        app.dependency_overrides[get_storage_service] = lambda: FakeStorage()
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/media/upload",
                files={"file": ("doc.pdf", b"fake-pdf-bytes", "application/pdf")},
            )
        finally:
            app.dependency_overrides[get_current_user] = original
            app.dependency_overrides.pop(get_storage_service, None)

        assert response.status_code == 400

    async def test_upload_media_auto_increments_sort_order(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        class FakeStorage:
            def build_storage_key(self, product_id: int, filename: str) -> str:
                return f"products/{product_id}/abc_{filename}"

            async def upload_file(self, key: str, data: bytes, content_type: str) -> None:
                pass

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        app.dependency_overrides[get_storage_service] = lambda: FakeStorage()
        try:
            r1 = await client.post(
                f"/api/v1/product/{product_id}/media/upload",
                files={"file": ("a.jpg", b"img", "image/jpeg")},
            )
            r2 = await client.post(
                f"/api/v1/product/{product_id}/media/upload",
                files={"file": ("b.jpg", b"img", "image/jpeg")},
            )
        finally:
            app.dependency_overrides[get_current_user] = original
            app.dependency_overrides.pop(get_storage_service, None)

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["sortOrder"] == 10
        assert r2.json()["sortOrder"] == 20

    async def test_non_admin_cannot_update_media_sort_order(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/media",
                json={"mediaType": "image", "storageKey": "uploads/img.png", "sortOrder": 0},
            )
            media_id = create_resp.json()["id"]
        finally:
            app.dependency_overrides[get_current_user] = original

        async def override_founder():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_founder
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/media/{media_id}",
                json={"sortOrder": 99},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Team
    # ------------------------------------------------------------------

    async def test_list_team_is_public_for_approved_product(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/team")
        assert response.status_code == 200
        assert response.json() == []

    async def test_admin_can_create_team_member(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/team",
                json={"name": "Alice", "roleLabel": "Lead Engineer"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert data["status"] == "approved"

    async def test_non_admin_cannot_create_team_member(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/team",
                json={"name": "Bob", "roleLabel": "Designer"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_admin_can_update_team_member(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/team",
                json={"name": "Carol"},
            )
            member_id = create_resp.json()["id"]
            response = await client.patch(
                f"/api/v1/product/{product_id}/team/{member_id}",
                json={"roleLabel": "CTO"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["roleLabel"] == "CTO"

    async def test_admin_can_delete_team_member(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/team",
                json={"name": "Dave"},
            )
            member_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/team/{member_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    # ------------------------------------------------------------------
    # Backers
    # ------------------------------------------------------------------

    async def test_list_backers_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/backers")
        assert response.status_code == 200
        assert response.json() == []

    async def test_owner_can_create_backer(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/backers",
                json={"name": "Y Combinator"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        assert response.json()["name"] == "Y Combinator"

    async def test_non_owner_cannot_create_backer(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_other():
            return build_mock_user(UserRole.FOUNDER, user_id=2)

        app.dependency_overrides[get_current_user] = override_other
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/backers",
                json={"name": "Sneaky VC"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 400

    async def test_owner_can_delete_backer(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/backers",
                json={"name": "Sequoia"},
            )
            backer_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/backers/{backer_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    async def test_backers_list_after_create_and_delete(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            await client.post(f"/api/v1/product/{product_id}/backers", json={"name": "A16Z"})
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/backers", json={"name": "Stripe"}
            )
            backer_id = create_resp.json()["id"]
            list_resp = await client.get(f"/api/v1/product/{product_id}/backers")
            assert len(list_resp.json()) == 2

            await client.delete(f"/api/v1/product/{product_id}/backers/{backer_id}")
            list_resp = await client.get(f"/api/v1/product/{product_id}/backers")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert len(list_resp.json()) == 1

    # ------------------------------------------------------------------
    # Voices
    # ------------------------------------------------------------------

    async def test_list_voices_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/voices")
        assert response.status_code == 200
        assert response.json() == []

    async def test_admin_can_create_voice(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/voices",
                json={"quote": "Amazing product!", "authorHandle": "@user123"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["quote"] == "Amazing product!"
        assert data["authorHandle"] == "@user123"

    async def test_non_admin_cannot_create_voice(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/voices",
                json={"quote": "Sneaky testimonial", "authorHandle": "@sneaky"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_admin_can_update_voice(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/voices",
                json={"quote": "Old quote", "authorHandle": "@author"},
            )
            voice_id = create_resp.json()["id"]
            response = await client.patch(
                f"/api/v1/product/{product_id}/voices/{voice_id}",
                json={"quote": "New quote"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["quote"] == "New quote"

    async def test_admin_can_delete_voice(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/voices",
                json={"quote": "Delete me", "authorHandle": "@gone"},
            )
            voice_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/voices/{voice_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    # ------------------------------------------------------------------
    # Bounties
    # ------------------------------------------------------------------

    async def test_list_bounties_is_public(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        response = await client.get(f"/api/v1/product/{product_id}/bounties")
        assert response.status_code == 200
        assert response.json() == []

    async def test_admin_can_create_bounty(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/bounties",
                json={
                    "title": "Fix auth bug",
                    "rewardAmount": "500.00",
                    "externalUrl": "https://github.com/issues/1",
                },
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Fix auth bug"
        assert data["status"] == "open"
        assert data["rewardAmount"] == "500.00"

    async def test_non_admin_cannot_create_bounty(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, user_id=1)
        original = app.dependency_overrides[get_current_user]

        async def override_owner():
            return build_mock_user(UserRole.FOUNDER, user_id=1)

        app.dependency_overrides[get_current_user] = override_owner
        try:
            response = await client.post(
                f"/api/v1/product/{product_id}/bounties",
                json={
                    "title": "Sneaky bounty",
                    "rewardAmount": "100.00",
                    "externalUrl": "https://example.com",
                },
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 403

    async def test_admin_can_update_bounty(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/bounties",
                json={
                    "title": "Initial bounty",
                    "rewardAmount": "250.00",
                    "externalUrl": "https://github.com/issues/2",
                },
            )
            bounty_id = create_resp.json()["id"]
            response = await client.patch(
                f"/api/v1/product/{product_id}/bounties/{bounty_id}",
                json={"status": "completed"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    async def test_admin_can_delete_bounty(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            create_resp = await client.post(
                f"/api/v1/product/{product_id}/bounties",
                json={
                    "title": "Delete me",
                    "rewardAmount": "100.00",
                    "externalUrl": "https://github.com/issues/3",
                },
            )
            bounty_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/product/{product_id}/bounties/{bounty_id}")
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 204

    async def test_bounty_not_found_returns_404(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client)
        original = app.dependency_overrides[get_current_user]

        async def override_admin():
            return build_mock_user(UserRole.ADMIN, user_id=99)

        app.dependency_overrides[get_current_user] = override_admin
        try:
            response = await client.patch(
                f"/api/v1/product/{product_id}/bounties/999999",
                json={"status": "completed"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original

        assert response.status_code == 404
