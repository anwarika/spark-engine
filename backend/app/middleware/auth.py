"""
Auth middleware for Spark.

Supports two identity-passing strategies so integrators can choose what fits
their architecture:

1. Header-based (server-to-server, recommended for backends):
      X-Tenant-ID: acme-corp
      X-User-ID:   user-123

2. Bearer token (SDK / client-side friendly):
      Authorization: Bearer <base64(tenant_id:user_id)>

   The token is just base64(tenant_id:user_id). Integrators are expected to
   mint this on their backend and pass it to the browser — Spark never issues
   tokens directly. For stronger auth, integrators should proxy Spark behind
   their own API gateway and inject X-Tenant-ID / X-User-ID server-side.
"""
import base64
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/api/health", "/.well-known/agent.json"}


def _parse_bearer(token: str) -> tuple[str, str] | None:
    """
    Decode base64(tenant_id:user_id) Bearer token.
    Returns (tenant_id, user_id) or None if malformed.
    """
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
        # Skip health / well-known paths
        if request.url.path in _SKIP_PATHS:
            request.state.tenant_id = "default-tenant"
            request.state.user_id = "default-user"
            return await call_next(request)

        tenant_id: str | None = None
        user_id: str | None = None
        auth_method = "none"

        # 1. Try Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            parsed = _parse_bearer(token)
            if parsed:
                tenant_id, user_id = parsed
                auth_method = "bearer"
            else:
                logger.warning("Malformed Bearer token — falling back to headers")

        # 2. Fall back to explicit headers
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID") or "default-tenant"
        if not user_id:
            user_id = request.headers.get("X-User-ID") or "default-user"

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.auth_method = auth_method

        logger.debug(
            f"auth={auth_method} tenant={tenant_id} user={user_id} path={request.url.path}"
        )

        return await call_next(request)


def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", "default-tenant")


def get_user_id(request: Request) -> str:
    return getattr(request.state, "user_id", "default-user")
