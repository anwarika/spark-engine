from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID", "default-tenant")
        user_id = request.headers.get("X-User-ID", "default-user")

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        logger.info(f"Request from tenant={tenant_id}, user={user_id}, path={request.url.path}")

        response = await call_next(request)
        return response


def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", "default-tenant")


def get_user_id(request: Request) -> str:
    return getattr(request.state, "user_id", "default-user")
