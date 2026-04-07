from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies import get_current_user
from app.api.dependencies.auth import get_optional_user
from app.domain.user.model import User
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ProductStatus, UserRole
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
        assert isinstance(response.json(), list)

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

    async def test_create_product_forbidden_for_regular_user(self, client: ClientWithEmail):
        response = await client.post("/api/v1/product", json=PRODUCT_PAYLOAD)
        assert response.status_code == 403
        assert response.json()["detail"] == "Founder or admin role required"

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
        assert data["userId"] == 1
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
        assert data["userId"] == 1

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
        matching = [p for p in response.json() if p["id"] == product_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "pending"

    async def test_list_defaults_to_approved_only(self, client: ClientWithEmail):
        product_id = await self._create_product_as_founder(client, approve=False)
        response = await client.get("/api/v1/product")
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()]
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
        ids = [p["id"] for p in response.json()]
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
        ids = [p["id"] for p in response.json()]
        assert product_id in ids
