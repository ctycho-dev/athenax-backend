import pytest
import pytest_asyncio
import uuid


@pytest.fixture
def admin_credentials():
    """Admin login credentials."""
    return {
        "email": "admin@example.com",
        "password": "admin123"
    }


@pytest.fixture
def user_payload():
    """Sample user payload for creation."""
    return {
        "email": f"testuser{uuid.uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!",
        "name": "Test User",
        "role": "user"
    }


@pytest_asyncio.fixture
async def current_user_id():
    """Get current authenticated user's ID for delete self test."""
    return 1
