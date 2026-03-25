from datetime import datetime

import pytest
from fastapi import HTTPException, status

from app.api.dependencies import get_current_user
from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.main import app
from tests.conftest import ClientWithEmail


def build_mock_user(role: UserRole) -> UserOutSchema:
    return UserOutSchema(
        id=1,
        name="Test User",
        email="test@example.com",
        role=role,
        verified=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.asyncio
class TestAdminRBACAPI:
    async def test_university_list_is_public(self, client: ClientWithEmail):
        original_override = app.dependency_overrides[get_current_user]

        async def override_unauthorized_user():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_user] = override_unauthorized_user
        try:
            response = await client.get("/api/v1/university")
        finally:
            app.dependency_overrides[get_current_user] = original_override

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_lab_list_is_public(self, client: ClientWithEmail):
        original_override = app.dependency_overrides[get_current_user]

        async def override_unauthorized_user():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_user] = override_unauthorized_user
        try:
            response = await client.get("/api/v1/lab")
        finally:
            app.dependency_overrides[get_current_user] = original_override

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_university_create_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.post(
            "/api/v1/university",
            json={"name": "Uni", "country": "LKA", "focus": "Research"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_university_update_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.patch(
            "/api/v1/university/1",
            json={"focus": "Updated"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_university_delete_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.delete("/api/v1/university/1")

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_lab_create_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.post(
            "/api/v1/lab",
            json={
                "universityId": 1,
                "name": "AI Lab",
                "focus": "ML",
                "description": "Test",
                "active": True,
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_lab_update_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.patch(
            "/api/v1/lab/1",
            json={"focus": "Updated"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_lab_delete_forbidden_for_non_admin(self, client: ClientWithEmail):
        response = await client.delete("/api/v1/lab/1")

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"

    async def test_university_create_allowed_for_admin(self, client: ClientWithEmail):
        original_override = app.dependency_overrides[get_current_user]

        async def override_admin_user():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin_user
        try:
            response = await client.post(
                "/api/v1/university",
                json={"name": "Admin Uni", "country": "LKA", "focus": "AI"},
            )
        finally:
            app.dependency_overrides[get_current_user] = original_override

        assert response.status_code == 201

    async def test_lab_create_allowed_for_admin(self, client: ClientWithEmail):
        original_override = app.dependency_overrides[get_current_user]

        async def override_admin_user():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin_user
        try:
            university_response = await client.post(
                "/api/v1/university",
                json={"name": "Parent Uni", "country": "LKA", "focus": "Science"},
            )
            university_id = university_response.json()["id"]

            response = await client.post(
                "/api/v1/lab",
                json={
                    "universityId": university_id,
                    "name": "Admin Lab",
                    "focus": "AI",
                    "description": "Admin managed lab",
                    "active": True,
                },
            )
        finally:
            app.dependency_overrides[get_current_user] = original_override

        assert university_response.status_code == 201
        assert response.status_code == 201

    async def test_lab_create_returns_not_found_when_university_missing(
        self,
        client: ClientWithEmail,
    ):
        original_override = app.dependency_overrides[get_current_user]

        async def override_admin_user():
            return build_mock_user(UserRole.ADMIN)

        app.dependency_overrides[get_current_user] = override_admin_user
        try:
            response = await client.post(
                "/api/v1/lab",
                json={
                    "universityId": 999999,
                    "name": "Orphan Lab",
                    "focus": "ML",
                    "description": "Should fail cleanly",
                    "active": True,
                },
            )
        finally:
            app.dependency_overrides[get_current_user] = original_override

        assert response.status_code == 404
        assert response.json()["detail"] == "University with ID 999999 not found"
