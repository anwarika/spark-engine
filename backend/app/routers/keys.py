"""
/api/keys — API Key management.

Integrators create keys here. The raw key is returned ONCE on creation
(sk_live_<32-char-random>) and never stored — only its SHA-256 hash is
persisted. Subsequent requests use the raw key as a Bearer token.

Scopes
------
  generate  — POST /api/a2a/generate
  read      — GET  /api/components, /api/apps
  pin       — POST /api/apps/pin, POST /api/apps/{id}/regenerate
  admin     — /api/admin/* and key management (list/revoke all keys for tenant)

Default new key gets ['generate', 'read'] scopes.
"""
import hashlib
import secrets
import logging
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field

from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id, require_scope

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_SCOPES = {"generate", "read", "pin", "admin"}


# ── Request / Response models ──────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    label: str = Field(default="Default Key", max_length=80)
    scopes: List[str] = Field(default=["generate", "read"])
    rate_limit_rpm: int = Field(default=60, ge=1, le=10000)


class KeyResponse(BaseModel):
    id: str
    label: str
    key_prefix: str          # e.g. "sk_live_ab" — safe to display
    scopes: List[str]
    rate_limit_rpm: int
    created_at: str
    last_used_at: Optional[str]
    revoked: bool


class CreateKeyResponse(KeyResponse):
    key: str                 # raw key — shown ONCE, then gone


# ── Helpers ────────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _row_to_response(row: dict) -> KeyResponse:
    return KeyResponse(
        id=str(row["id"]),
        label=row["label"],
        key_prefix=row["key_prefix"],
        scopes=list(row["scopes"]),
        rate_limit_rpm=row["rate_limit_rpm"],
        created_at=str(row["created_at"]),
        last_used_at=str(row["last_used_at"]) if row.get("last_used_at") else None,
        revoked=bool(row.get("revoked_at")),
    )


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=CreateKeyResponse, dependencies=[Depends(require_scope("admin"))])
async def create_key(request: Request, body: CreateKeyRequest):
    """Create a new API key. The raw key is returned once — store it safely."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)

    invalid = set(body.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid scopes: {invalid}")

    raw_key = "sk_live_" + secrets.token_urlsafe(32)
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]  # "sk_live_xxxx"

    storage = get_storage()
    try:
        row = await storage.create_api_key({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "label": body.label,
            "scopes": body.scopes,
            "rate_limit_rpm": body.rate_limit_rpm,
        })
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

    return CreateKeyResponse(
        **_row_to_response(row).model_dump(),
        key=raw_key,
    )


@router.get("", response_model=List[KeyResponse], dependencies=[Depends(require_scope("admin"))])
async def list_keys(request: Request):
    """List all active (non-revoked) API keys for the current tenant/user."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    rows = await storage.list_api_keys(tenant_id, user_id)
    return [_row_to_response(r) for r in rows]


@router.delete("/{key_id}", status_code=204, dependencies=[Depends(require_scope("admin"))])
async def revoke_key(key_id: str, request: Request):
    """Revoke an API key. Revoked keys are rejected immediately on next use."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    ok = await storage.revoke_api_key(key_id, tenant_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
