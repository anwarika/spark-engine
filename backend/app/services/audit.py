"""
Audit logging service.

Writes a structured entry to the audit_log table for every significant action.
All writes are fire-and-forget (asyncio.ensure_future) so they never block
the hot path. Failures are logged at WARNING level but never raised.

Usage:
    from app.services.audit import audit_log
    await audit_log(request, action="generate", resource_id=component_id)
"""
import asyncio
import logging
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _write(entry: dict):
    try:
        from app.database import get_storage
        storage = get_storage()
        await storage.write_audit_log(entry)
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")


def audit_log(
    request: Request,
    action: str,
    resource_id: Optional[str] = None,
    status_code: Optional[int] = 200,
    meta: Optional[dict] = None,
):
    """
    Fire-and-forget audit log write. Safe to call from any async context.

    Args:
        request:      The FastAPI Request (used to extract tenant/user/key/ip).
        action:       Short action name, e.g. 'generate', 'pin', 'key.create'.
        resource_id:  ID of the affected resource (component_id, pin_id, …).
        status_code:  HTTP status code of the response (optional).
        meta:         Additional structured data to store in the JSONB `meta` column.
    """
    entry = {
        "tenant_id": getattr(request.state, "tenant_id", "unknown"),
        "user_id": getattr(request.state, "user_id", "unknown"),
        "key_id": getattr(request.state, "key_id", None),
        "action": action,
        "resource_id": resource_id,
        "ip": _get_client_ip(request),
        "status_code": status_code,
        "meta": meta or {},
    }
    asyncio.ensure_future(_write(entry))
