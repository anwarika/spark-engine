"""
Rate limiting middleware for Spark.

Per-key limits: stored in the api_keys row (rate_limit_rpm).
Default fallback: settings.rate_limit_requests_per_minute (for header/legacy auth).

Uses a simple Redis sliding-window counter (INCR + EXPIRE).
Degrades gracefully: if Redis is unavailable, rate limiting is skipped.
"""
import logging
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# Paths that are exempt from rate limiting
_EXEMPT_PATHS = {"/api/health", "/api/ready", "/.well-known/agent.json"}


async def _get_redis():
    """Return the shared Redis client, or None if unavailable."""
    try:
        from app.database import get_redis
        return await get_redis()
    except Exception:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Determine limit and bucket key
        auth_method = getattr(request.state, "auth_method", "none")
        key_id = getattr(request.state, "key_id", None)
        tenant_id = getattr(request.state, "tenant_id", "default-tenant")
        user_id = getattr(request.state, "user_id", "default-user")

        # Per-key RPM comes from the API key row (already stored in state by auth middleware)
        rpm_limit = getattr(request.state, "rate_limit_rpm", None) or settings.rate_limit_requests_per_minute

        if key_id:
            bucket = f"rl:key:{key_id}"
        else:
            bucket = f"rl:tenant:{tenant_id}:user:{user_id}"

        window = 60  # seconds
        now_window = int(time.time()) // window

        try:
            redis = await _get_redis()
            if redis is not None:
                redis_key = f"{bucket}:{now_window}"
                count = await redis.incr(redis_key)
                if count == 1:
                    await redis.expire(redis_key, window * 2)

                if count > rpm_limit:
                    retry_after = window - (int(time.time()) % window)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": f"Rate limit exceeded. Max {rpm_limit} requests/minute.",
                            "retry_after": retry_after,
                        },
                        headers={"Retry-After": str(retry_after)},
                    )
        except Exception as e:
            logger.warning(f"Rate limit check failed (skipping): {e}")

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rpm_limit)
        return response
