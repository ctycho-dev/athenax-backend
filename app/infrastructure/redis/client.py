from redis.asyncio import Redis, ConnectionError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger()


class RedisClient:
    def __init__(self):
        self._client = Redis.from_url(
            settings.redis.url,
            decode_responses=True,
            max_connections=20,
        )

    async def ping(self) -> None:
        try:
            await self._client.ping()  # type: ignore[misc]
        except ConnectionError as e:
            logger.error("Could not connect to Redis: %s", e)
            raise

    async def get(self, key: str) -> str | None:
        try:
            return await self._client.get(key)  # type: ignore[return-value]
        except Exception:
            logger.warning("Redis get failed for key %s", key)
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._client.set(key, value, ex=ttl_seconds)  # type: ignore[misc]
        except Exception:
            logger.warning("Redis set failed for key %s", key)

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)  # type: ignore[misc]
        except Exception:
            logger.warning("Redis delete failed for key %s", key)

    async def delete_by_pattern(self, pattern: str) -> None:
        # Finds and deletes all keys matching the pattern (e.g. "article:list:*") in batches, without blocking Redis
        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)  # type: ignore[misc]
                if keys:
                    await self._client.delete(*keys)  # type: ignore[misc]
                if cursor == 0:
                    break
        except Exception:
            logger.warning("Redis delete_by_pattern failed for pattern %s", pattern)

    async def close(self) -> None:
        await self._client.aclose()

