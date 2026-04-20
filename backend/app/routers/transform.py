"""
/api/transform — Python Data Transform Layer (powered by pydantic-monty).

Endpoints:

  POST /api/components/{id}/data/transform
    Generate Python code + execute + cache result in Data Bridge (Redis).
    The component then fetches its data normally via the existing Data Bridge.

  POST /api/transform/preview
    Execute without caching. Useful from the Playground or for debugging.
    Returns the executed code + transformed output.

  GET /api/components/{id}/data/transform/code
    Return the last generated transform code for a component (stored in Redis
    alongside the data). Good for transparency / debugging by integrators.

Auth: requires 'generate' scope (same as component generation).
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.database import get_redis, get_storage
from app.middleware.auth import get_tenant_id, get_user_id, require_scope
from app.services.audit import audit_log
from app.services.transform import TransformError, TransformService

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton — reuses the LLMGateway connection
_transform_service: Optional[TransformService] = None


def _get_service() -> TransformService:
    global _transform_service
    if _transform_service is None:
        _transform_service = TransformService()
    return _transform_service


# ── Request / Response models ────────────────────────────────────────────────

class TransformRequest(BaseModel):
    raw_data: Dict[str, Any] = Field(
        ...,
        description="The raw dataset to transform. Any shape — top-level keys are summarised for the LLM.",
    )
    transform: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Plain-English description of what to compute. E.g. 'Top 5 products by revenue this month'.",
    )
    ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="How long to cache the result in Redis (60s–24h). Default 1 hour.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, execute but do NOT cache. Useful for preview/testing.",
    )


class PreviewRequest(BaseModel):
    raw_data: Dict[str, Any]
    transform: str = Field(..., min_length=5, max_length=500)


class TransformResponse(BaseModel):
    status: str
    output_keys: list
    execution_ms: float
    cached: bool
    component_id: Optional[str] = None
    ttl_seconds: Optional[int] = None


class PreviewResponse(BaseModel):
    status: str
    code: str
    result: Dict[str, Any]
    output_keys: list
    execution_ms: float


# ── Helpers ───────────────────────────────────────────────────────────────────

_CODE_KEY_SUFFIX = ":transform_code"


async def _cache_result(
    tenant_id: str,
    component_id: str,
    result: Dict[str, Any],
    code: str,
    ttl: int,
):
    """Store transform result + code in Redis under the Data Bridge key."""
    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis is unavailable — cannot cache transform result")

    data_key = f"databridge:{tenant_id}:{component_id}:real"
    code_key = f"{data_key}{_CODE_KEY_SUFFIX}"
    try:
        await redis.setex(data_key, ttl, json.dumps(result))
        await redis.setex(code_key, ttl, code)
        logger.info(f"Cached transform result for component={component_id} ttl={ttl}s keys={list(result.keys())}")
    except Exception as e:
        logger.error(f"Failed to cache transform result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cache transform result: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/components/{component_id}/data/transform",
    response_model=TransformResponse,
    dependencies=[Depends(require_scope("generate"))],
)
async def transform_component_data(
    component_id: str,
    request: Request,
    body: TransformRequest,
):
    """
    Transform raw data with LLM-generated Python (Monty sandbox) and cache the
    result in the Data Bridge so the component renders with real computed data.

    The component fetches its data normally — no code changes in the component.
    """
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    component = await storage.get_component(component_id, tenant_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    svc = _get_service()
    try:
        result, elapsed_ms, code = await svc.run(body.raw_data, body.transform)
    except TransformError as e:
        logger.warning(f"Transform failed for component={component_id}: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(e),
                "code": e.code,
                "hint": "Try rephrasing the transform description or check that raw_data has the expected keys.",
            },
        )

    cached = not body.dry_run
    if cached:
        await _cache_result(tenant_id, component_id, result, code, body.ttl_seconds)

    audit_log(
        request,
        action="transform",
        resource_id=component_id,
        meta={
            "transform": body.transform[:120],
            "output_keys": list(result.keys()),
            "execution_ms": round(elapsed_ms, 2),
            "cached": cached,
        },
    )

    return TransformResponse(
        status="ok",
        output_keys=list(result.keys()),
        execution_ms=round(elapsed_ms, 2),
        cached=cached,
        component_id=component_id,
        ttl_seconds=body.ttl_seconds if cached else None,
    )


@router.post(
    "/transform/preview",
    response_model=PreviewResponse,
    dependencies=[Depends(require_scope("generate"))],
)
async def preview_transform(
    request: Request,
    body: PreviewRequest,
):
    """
    Run a transform without tying it to a component or caching the result.
    Returns the generated Python code + the transformed output.
    Perfect for the Playground 'Transform' tab.
    """
    svc = _get_service()
    try:
        result, elapsed_ms, code = await svc.run(body.raw_data, body.transform)
    except TransformError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(e),
                "code": e.code,
                "hint": "Check that raw_data has the expected keys and the transform description is clear.",
            },
        )

    return PreviewResponse(
        status="ok",
        code=code,
        result=result,
        output_keys=list(result.keys()),
        execution_ms=round(elapsed_ms, 2),
    )


@router.get(
    "/components/{component_id}/data/transform/code",
    dependencies=[Depends(require_scope("read"))],
)
async def get_transform_code(component_id: str, request: Request):
    """
    Return the last Python transform code generated for a component.
    Useful for integrators who want to inspect or audit what ran.
    Only available while the Data Bridge result is still cached in Redis.
    """
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    component = await storage.get_component(component_id, tenant_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis is unavailable")

    code_key = f"databridge:{tenant_id}:{component_id}:real{_CODE_KEY_SUFFIX}"
    code = await redis.get(code_key)
    if code is None:
        raise HTTPException(
            status_code=404,
            detail="No cached transform code found. Either no transform has been run, or it has expired.",
        )

    ttl = await redis.ttl(code_key)
    return {
        "component_id": component_id,
        "code": code,
        "expires_in_seconds": ttl,
    }
