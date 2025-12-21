from supabase import create_client, Client
from app.config import settings
import redis.asyncio as redis
from typing import Optional


_supabase_client: Optional[Client] = None
_redis_client: Optional[redis.Redis] = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        # Use service role key if available (bypasses RLS for development)
        # Otherwise fall back to anon key
        key = settings.supabase_service_role_key or settings.supabase_anon_key
        _supabase_client = create_client(
            settings.supabase_url,
            key
        )
    return _supabase_client


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except Exception as e:
            import logging
            logging.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            _redis_client = None
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
