import time
from fastapi import Request, HTTPException
from app.infrastructure.redis.redis_client import redis_client


async def rate_limiter(request: Request, call_next):
    """Basic rate limiter by host + endpoint"""
    try:
        # Get client host (works behind proxies if configured properly)
        host = request.client.host if request.client else "unknown_host"
        print(host)
        # Get the endpoint path
        endpoint = request.url.path
        print(endpoint)
        
        # Create a unique key
        window = 60  # seconds
        time_window = int(time.time() // window)
        key = f"rate_limit:{host}:{endpoint}:{time_window}"
        
        # Default limits (adjust as needed)
        limit = 100 if endpoint.startswith("/api/") else 200
        
        # Atomic increment and check
        current = await redis_client.incr(key)
        if current == 1:  # Only set expire on first hit
            await redis_client.expire(key, window)
        
        if current > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} requests per minute",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(time_window * window + window)
                }
            )
            
        response = await call_next(request)
        response.headers.update({
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current))
        })
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Rate limiter error: {e}")
        return await call_next(request)
