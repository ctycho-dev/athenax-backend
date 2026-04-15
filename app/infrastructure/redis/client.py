from redis.asyncio import Redis, ConnectionError
from app.core.config import settings
from app.core.logger import get_logger
from fastapi import Request


logger = get_logger()


class RedisClient:
    def __init__(self):
        self._client = Redis.from_url(settings.redis.url, decode_responses=False)

    async def ping(self) -> None:
        try:
            await self._client.ping()  # type: ignore[misc]
        except ConnectionError as e:
            logger.error("Could not connect to Redis: %s", e)
            raise

    async def close(self) -> None:
        await self._client.aclose()


def get_redis_client(request: Request) -> RedisClient:
    """FastAPI dependency — returns the RedisClient stored on app.state."""
    return request.app.state.redis_client
