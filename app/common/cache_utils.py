import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel

from app.infrastructure.redis.client import RedisClient

S = TypeVar("S", bound=BaseModel)


async def cached_list(
    redis: RedisClient | None,
    key: str,
    ttl: int,
    schema_class: type[S],
    fetch_fn: Callable[[], Awaitable[list]],
    *,
    from_attributes: bool = False,
) -> list[S]:
    """Cache-aside for public list endpoints. Always returns schema instances.

    Pass from_attributes=True when the service returns ORM objects rather than schemas.
    """
    if redis is None:
        return await fetch_fn()

    cached = await redis.get(key)
    if cached:
        return [schema_class.model_validate(item) for item in json.loads(cached)]

    result = await fetch_fn()
    schemas = [schema_class.model_validate(item, from_attributes=from_attributes) for item in result]
    await redis.set(key, json.dumps([s.model_dump(mode="json") for s in schemas]), ttl_seconds=ttl)
    return schemas


async def cached_detail(
    redis: RedisClient | None,
    key: str,
    ttl: int,
    schema_class: type[S],
    fetch_fn: Callable[[], Awaitable],
    *,
    from_attributes: bool = False,
) -> S:
    """Try Redis first; on miss, fetch from DB, cache it, then return. Skips cache if Redis is unavailable."""
    if redis is None:
        return await fetch_fn()

    cached = await redis.get(key)
    if cached:
        return schema_class.model_validate(json.loads(cached))

    result = await fetch_fn()
    schema = schema_class.model_validate(result, from_attributes=from_attributes)
    await redis.set(key, json.dumps(schema.model_dump(mode="json")), ttl_seconds=ttl)
    return schema
