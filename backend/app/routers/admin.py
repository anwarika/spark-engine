"""
/api/admin — Usage stats and tenant-level admin endpoints.
Requires 'admin' scope on API key (or header auth for dev).
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Depends

from app.database import get_storage, get_redis
from app.middleware.auth import get_tenant_id, require_scope
from app.storage import PostgresStorage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", dependencies=[Depends(require_scope("admin"))])
async def get_stats(request: Request, days: int = 7):
    """
    Usage stats for the current tenant.

    Returns:
    - components_generated: total & today
    - active_pins: count of live pinned apps
    - top_prompts: most common prompt prefixes (from component names)
    - api_keys: count of active keys
    """
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    # ── Component counts ──
    try:
        all_result = await storage.list_components(tenant_id, limit=1, offset=0, status="active")
        total_components = all_result.get("total", 0)
    except Exception:
        total_components = 0

    # ── Pinned apps ──
    try:
        from app.middleware.auth import get_user_id
        user_id = get_user_id(request)
        pins = await storage.list_pinned_apps(tenant_id, user_id)
        active_pins = len(pins)
    except Exception:
        active_pins = 0

    # ── API key count ──
    try:
        from app.middleware.auth import get_user_id
        user_id = get_user_id(request)
        keys = await storage.list_api_keys(tenant_id, user_id)
        active_keys = len(keys)
    except Exception:
        active_keys = 0

    # ── Redis info ──
    redis_info: dict = {}
    redis_client = await get_redis()
    if redis_client:
        try:
            info = await redis_client.info("stats")
            redis_info = {
                "cache_hits": info.get("keyspace_hits", 0),
                "cache_misses": info.get("keyspace_misses", 0),
            }
        except Exception:
            pass

    # ── Postgres-specific: generation trend ──
    generation_trend: list = []
    if isinstance(storage, PostgresStorage):
        try:
            pool = await storage._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DATE(created_at) AS day, COUNT(*) AS count
                    FROM components
                    WHERE tenant_id = $1
                      AND created_at >= NOW() - ($2 || ' days')::interval
                    GROUP BY day
                    ORDER BY day ASC
                """, tenant_id, str(days))
                generation_trend = [
                    {"date": str(r["day"]), "count": int(r["count"])} for r in rows
                ]
        except Exception as e:
            logger.warning(f"Could not fetch generation trend: {e}")

    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "components": {
            "total_active": total_components,
            "trend": generation_trend,
        },
        "active_pins": active_pins,
        "active_api_keys": active_keys,
        "cache": redis_info,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
