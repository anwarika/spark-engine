from __future__ import annotations

import asyncio
import gzip as gzip_lib
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response

from app.database import get_redis
from app.middleware.auth import get_tenant_id, get_user_id
from app.services.mock_data import MockSpec, generate_mock_dataset

logger = logging.getLogger(__name__)
router = APIRouter()

# Very small in-process cache (useful even if Redis is absent)
_MEM_CACHE: Dict[str, str] = {}
_MEM_CACHE_ORDER: list[str] = []
_MEM_CACHE_MAX = 8


def _make_cache_key(tenant_id: str, spec: MockSpec) -> str:
    return f"mock:{tenant_id}:{spec.profile}:{spec.scale}:{spec.seed}:{spec.days}:json"


def _mem_cache_get(key: str) -> Optional[str]:
    return _MEM_CACHE.get(key)


def _mem_cache_put(key: str, value: str) -> None:
    if key in _MEM_CACHE:
        _MEM_CACHE[key] = value
        return
    _MEM_CACHE[key] = value
    _MEM_CACHE_ORDER.append(key)
    while len(_MEM_CACHE_ORDER) > _MEM_CACHE_MAX:
        old = _MEM_CACHE_ORDER.pop(0)
        _MEM_CACHE.pop(old, None)


@router.get("/mock/datasets")
async def list_mock_datasets():
    return {
        "profiles": ["ecommerce", "saas", "marketing", "finance", "sales"],
        "scales": ["small", "medium", "large", "xl"],
        "notes": [
            "Use /api/mock/download to download JSON (optionally gzip).",
            "Use POST /api/components/{component_id}/data with body.mock to return the same datasets to micro-apps.",
            "Profiles: saas(marketing/retention), marketing(attribution), finance(P&L), sales(pipeline).",
        ],
    }


@router.get("/mock/download")
async def download_mock_data(
    request: Request,
    profile: str = "ecommerce",
    scale: str = "medium",
    seed: int = 1,
    days: int = 180,
    gzip: bool = True,
    cache: bool = True,
    latency_ms: int = 0,
):
    """
    Download a deterministic mock dataset for dashboard testing.

    Returns: application/json (optionally Content-Encoding: gzip)
    """
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)

    spec = MockSpec(profile=profile, scale=scale, seed=int(seed), days=int(days))
    cache_key = _make_cache_key(tenant_id, spec)

    if latency_ms and latency_ms > 0:
        await asyncio.sleep(min(latency_ms, 60_000) / 1000.0)

    payload_str: Optional[str] = None

    if cache:
        payload_str = _mem_cache_get(cache_key)
        if payload_str is None:
            redis_client = await get_redis()
            if redis_client:
                try:
                    payload_str = await redis_client.get(cache_key)
                except Exception as e:
                    logger.warning(f"Mock redis cache get failed: {e}")

    if payload_str is None:
        data = generate_mock_dataset(spec)
        data["meta"]["requested_by"] = {"tenant_id": tenant_id, "user_id": user_id}
        payload_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        if cache:
            _mem_cache_put(cache_key, payload_str)
            redis_client = await get_redis()
            if redis_client:
                try:
                    # Keep TTL modest; these payloads can be large
                    await redis_client.set(cache_key, payload_str, ex=3600)
                except Exception as e:
                    logger.warning(f"Mock redis cache set failed: {e}")

    if gzip:
        gz = gzip_lib.compress(payload_str.encode("utf-8"), compresslevel=6)
        return Response(
            content=gz,
            media_type="application/json",
            headers={
                "Content-Encoding": "gzip",
                "Content-Disposition": f'attachment; filename="spark-mock-{spec.profile}-{spec.scale}-{spec.seed}-{spec.days}d.json.gz"',
            },
        )

    return Response(
        content=payload_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="spark-mock-{spec.profile}-{spec.scale}-{spec.seed}-{spec.days}d.json"',
        },
    )


