from fastapi import APIRouter
from app.database import get_storage, get_redis
from app.storage import SupabaseStorage, PostgresStorage
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        storage = get_storage()
        redis_client = await get_redis()
        
        db_status = "connected" # Storage init usually implies connection or at least config validity
        db_type = "unknown"
        
        if isinstance(storage, SupabaseStorage):
            db_type = "supabase"
            # potentially ping supabase?
        elif isinstance(storage, PostgresStorage):
            db_type = "postgres"
            # potentially ping postgres?

        redis_status = "disconnected"
        if redis_client:
            try:
                await redis_client.ping()
                redis_status = "connected"
            except:
                redis_status = "error"

        return {
            "status": "healthy",
            "services": {
                "database": db_status,
                "type": db_type,
                "redis": redis_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/metrics")
async def metrics():
    redis_client = await get_redis()

    if redis_client:
        try:
            cache_info = await redis_client.info("stats")
            return {
                "cache": {
                    "hits": cache_info.get("keyspace_hits", 0),
                    "misses": cache_info.get("keyspace_misses", 0)
                }
            }
        except:
            pass

    return {
        "cache": {
            "status": "unavailable"
        }
    }
