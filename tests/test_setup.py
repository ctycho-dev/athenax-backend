import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Test that database connection works."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_client_works(client):
    """Test that test client works."""
    # This will 404 but proves client is working
    response = await client.get("/health")
    assert response.status_code in [200, 404]
