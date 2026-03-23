import pytest
from tests.conftest import ClientWithEmail


@pytest.mark.asyncio
class TestUserAPI:
    """Integration tests for User authentication and CRUD operations."""

    async def test_create_user_success(self, client: ClientWithEmail, user_payload):
        """Test successful user creation."""
        response = await client.post("/api/v1/user/", json=user_payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_payload["email"]
        assert "id" in data
        assert data["verified"] is False
        assert "password" not in data

    async def test_create_user_duplicate_email(self, client: ClientWithEmail, user_payload):
        """Test creating user with duplicate email fails."""
        await client.post("/api/v1/user/", json=user_payload)
        response = await client.post("/api/v1/user/", json=user_payload)
        
        assert response.status_code == 409

    async def test_get_all_users(self, client: ClientWithEmail):
        """Test retrieving all users."""
        response = await client.get("/api/v1/user/")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_user_by_id(self, client: ClientWithEmail, user_payload):
        """Test retrieving user by ID."""
        create_response = await client.post("/api/v1/user/", json=user_payload)

        user_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/user/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == user_payload["email"]

    async def test_get_user_not_found(self, client: ClientWithEmail):
        """Test retrieving user with non-existent ID."""
        non_existent_id = 99999
        
        response = await client.get(f"/api/v1/user/{non_existent_id}")
        
        assert response.status_code == 404

    async def test_delete_user_success(self, client: ClientWithEmail, user_payload):
        """Test successful user deletion."""
        create_response = await client.post("/api/v1/user/", json=user_payload)
        user_id = create_response.json()["id"]
        
        delete_response = await client.delete(f"/api/v1/user/{user_id}")
        
        assert delete_response.status_code == 204
        
        get_response = await client.get(f"/api/v1/user/{user_id}")
        
        assert get_response.status_code == 404

    async def test_delete_user_not_found(self, client: ClientWithEmail):
        """Test deleting non-existent user."""
        non_existent_id = 99999
        
        response = await client.delete(f"/api/v1/user/{non_existent_id}")
        
        assert response.status_code == 404
