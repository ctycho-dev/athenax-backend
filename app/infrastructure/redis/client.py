from redis.asyncio import Redis, ConnectionError
from app.core.config import settings
from tenacity import retry, wait_fixed, stop_after_delay
from app.core.logger import get_logger


logger = get_logger()


# Initialize the Redis client
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    username="default"
)


@retry(wait=wait_fixed(2), stop=stop_after_delay(30), reraise=True)
async def connect_to_redis() -> Redis:
    """Ensure the Redis client can connect."""
    try:
        await redis_client.ping()
        return redis_client
    except ConnectionError as e:
        logger.error(f"Could not connect to Redis: {e}")
        raise RuntimeError(f"Could not connect to Redis: {e}") from e


async def get_redis_client() -> Redis:
    """Get Redis client with a retry mechanism."""
    try:
        return await connect_to_redis()
    except ConnectionError as e:
        logger.error(f"Could not connect to Redis: {e}")
        raise RuntimeError(f"Could not connect to Redis: {e}") from e
