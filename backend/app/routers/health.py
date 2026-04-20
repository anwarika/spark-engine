from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app import __version__
from app.config import settings
from app.database import get_storage, get_redis
from app.storage import SupabaseStorage, PostgresStorage
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


async def _check_postgres(storage: PostgresStorage) -> str:
    try:
        pool = await asyncio.wait_for(storage._get_pool(), timeout=3)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return "ok"
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as e:
        return f"error: {e}"


async def _check_llm() -> str:
    """Light reachability check — just verifies the LLM base URL resolves."""
    import httpx
    base = settings.llm_base_url or "https://api.openai.com"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(base.rstrip("/") + "/")
            return "ok" if r.status_code < 500 else f"http_{r.status_code}"
    except Exception as e:
        return f"error: {type(e).__name__}"


@router.get("/health")
async def health_check():
    """Basic liveness check — returns 200 even if dependencies are degraded."""
    try:
        storage = get_storage()
        redis_client = await get_redis()

        db_type = "supabase" if isinstance(storage, SupabaseStorage) else "postgres"

        redis_status = "disconnected"
        if redis_client:
            try:
                await asyncio.wait_for(redis_client.ping(), timeout=2)
                redis_status = "ok"
            except Exception:
                redis_status = "error"

        return {
            "status": "healthy",
            "version": __version__,
            "environment": settings.environment,
            "services": {
                "database": db_type,
                "redis": redis_status,
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns 200 only when all required dependencies are reachable.
    Used to gate traffic: do not route requests here until /ready is green.
    """
    checks: dict[str, str] = {}
    healthy = True

    # Postgres
    storage = get_storage()
    if isinstance(storage, PostgresStorage):
        result = await _check_postgres(storage)
        checks["postgres"] = result
        if result != "ok":
            healthy = False
    else:
        checks["database"] = "supabase (assumed ok)"

    # Redis (non-fatal — app degrades gracefully)
    redis_client = await get_redis()
    if redis_client:
        try:
            await asyncio.wait_for(redis_client.ping(), timeout=2)
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"
    else:
        checks["redis"] = "unavailable"

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": healthy,
            "checks": checks,
            "version": __version__,
        },
    )


@router.get("/metrics")
async def metrics():
    redis_client = await get_redis()

    if redis_client:
        try:
            cache_info = await redis_client.info("stats")
            return {
                "cache": {
                    "hits": cache_info.get("keyspace_hits", 0),
                    "misses": cache_info.get("keyspace_misses", 0),
                }
            }
        except Exception:
            pass

    return {"cache": {"status": "unavailable"}}
