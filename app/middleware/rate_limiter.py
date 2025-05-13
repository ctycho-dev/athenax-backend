# app/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status

from app.core.config import settings


# Create a custom key function if needed (e.g., user-based limits)
def rate_limit_key(request: Request):

    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user}"
    return get_remote_address(request)


# Initialize limiter with Redis storage
limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["200/minute", "20/second"],
    storage_uri=f"redis://{settings.redis_host}:{settings.redis_port}",
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please try again later.",
    )
