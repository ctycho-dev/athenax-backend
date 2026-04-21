from fastapi import Request
from app.infrastructure.redis.client import RedisClient


def get_redis_client(request: Request) -> RedisClient:
    """FastAPI dependency — returns the RedisClient stored on app.state."""
    return request.app.state.redis_client