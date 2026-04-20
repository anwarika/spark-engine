"""
Auth middleware for Spark.

Supports three identity-passing strategies:

1. API Key (recommended for production integrators):
      Authorization: Bearer sk_live_<random>
   Key is hashed and looked up in the api_keys table. Scopes and rate limits
   are read from the key row. Revoked keys are rejected immediately.

2. Header-based (server-to-server legacy, fine for trusted backends):
      X-Tenant-ID: acme-corp
      X-User-ID:   user-123

3. Base64 Bearer token (legacy SDK compatibility):
      Authorization: Bearer <base64(tenant_id:user_id)>

For new integrations, use API Keys (#1). The SDK's SparkClient.create()
accepts an API key and sends it as Bearer sk_live_*.
"""
import base64
import hashlib
import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/api/health", "/api/ready", "/.well-known/agent.json"}

# Injected by main.py after storage is initialized to avoid circular imports
_storage = None


def set_storage(storage):
    global _storage
    _storage = storage


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_base64_bearer(token: str) -> tuple[str, str] | None:
    """Decode legacy base64(tenant_id:user_id) Bearer token."""
    try:
        decoded = base64.b64decode(token + "==").decode("utf-8")
        parts = decoded.split(":", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
    except Exception:
        pass
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            request.state.tenant_id = "default-tenant"
            request.state.user_id = "default-user"
            request.state.auth_method = "skip"
            request.state.key_id = None
            request.state.scopes = ["generate", "read", "pin", "admin"]
            return await call_next(request)

        tenant_id: Optional[str] = None
        user_id: Optional[str] = None
        auth_method = "none"
        key_id = None
        scopes = ["generate", "read", "pin", "admin"]  # default: full access for header auth

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

            if token.startswith("sk_live_") and _storage is not None:
                # API Key path
                key_hash = _hash_key(token)
                try:
                    key_row = await _storage.get_api_key_by_hash(key_hash)
                except Exception as e:
                    logger.warning(f"API key lookup failed: {e}")
                    key_row = None

                if key_row and not key_row.get("revoked_at"):
                    tenant_id = key_row["tenant_id"]
                    user_id = key_row["user_id"]
                    key_id = str(key_row["id"])
                    scopes = list(key_row.get("scopes") or [])
                    request.state.rate_limit_rpm = key_row.get("rate_limit_rpm", 60)
                    auth_method = "api_key"
                    # Update last_used_at async (fire-and-forget)
                    try:
                        import asyncio
                        asyncio.ensure_future(_storage.touch_api_key(key_id))
                    except Exception:
                        pass
                else:
                    logger.warning("Invalid or revoked API key")

            else:
                # Legacy base64 Bearer
                parsed = _parse_base64_bearer(token)
                if parsed:
                    tenant_id, user_id = parsed
                    auth_method = "bearer"
                else:
                    logger.warning("Malformed Bearer token — falling back to headers")

        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID") or "default-tenant"
        if not user_id:
            user_id = request.headers.get("X-User-ID") or "default-user"

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.auth_method = auth_method
        request.state.key_id = key_id
        request.state.scopes = scopes

        logger.debug(
            f"auth={auth_method} tenant={tenant_id} user={user_id} "
            f"key_id={key_id} path={request.url.path}"
        )

        return await call_next(request)


# ── Dependency helpers ─────────────────────────────────────────────────────

def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", "default-tenant")


def get_user_id(request: Request) -> str:
    return getattr(request.state, "user_id", "default-user")


def get_key_id(request: Request) -> Optional[str]:
    return getattr(request.state, "key_id", None)


def get_scopes(request: Request) -> list:
    return getattr(request.state, "scopes", [])


def require_scope(scope: str):
    """FastAPI dependency factory: raises 403 if the request lacks the required scope."""
    def _check(request: Request):
        scopes = get_scopes(request)
        if scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"API key missing required scope: '{scope}'"
            )
    return _check
