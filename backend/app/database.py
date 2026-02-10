from app.config import settings
import redis.asyncio as redis
from typing import Optional
import logging
from app.storage import Storage, SupabaseStorage, PostgresStorage

_storage: Optional[Storage] = None
_redis_client: Optional[redis.Redis] = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        if settings.database_mode == "supabase":
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise ValueError("Supabase URL and Key are required for supabase mode")
            key = settings.supabase_service_role_key or settings.supabase_anon_key
            _storage = SupabaseStorage(settings.supabase_url, key)
            logging.info("Initialized Supabase storage")
        else:
            # Postgres mode
            _storage = PostgresStorage(settings.database_url)
            logging.info("Initialized Postgres storage")
            
    return _storage


# For backward compatibility if needed, though we should migrate away
def get_supabase():
    storage = get_storage()
    if isinstance(storage, SupabaseStorage):
        return storage.client
    raise RuntimeError("Current storage mode is not Supabase")


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
            logging.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            _redis_client = None
    return _redis_client


async def close_connections():
    global _redis_client, _storage
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    # Storage closing logic if needed (e.g. pool close)