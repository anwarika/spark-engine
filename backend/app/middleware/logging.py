import logging
import json
import time
from datetime import datetime
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders


class StructuredLoggingMiddleware:
    """
    Pure ASGI logging middleware — compatible with StreamingResponse / SSE.

    BaseHTTPMiddleware buffers the entire response body before passing it on,
    which breaks server-sent event streams. This implementation hooks into the
    ASGI send channel so it can capture the status code from the response-start
    message without consuming the body.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = str(time.time())
        status_code = 500

        # Pull auth state that was set by AuthMiddleware (runs before logging in the stack)
        state = scope.get("state", {})

        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-request-id":
                request_id = header_value.decode()
                break

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            execution_time = (time.time() - start_time) * 1000
            # scope["state"] is populated by AuthMiddleware
            app_state = scope.get("state")
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "method": scope.get("method", ""),
                "path": scope.get("path", ""),
                "tenant_id": getattr(app_state, "tenant_id", None) if app_state else None,
                "user_id": getattr(app_state, "user_id", None) if app_state else None,
                "status_code": status_code,
                "execution_time_ms": round(execution_time, 2),
            }
            logging.info(json.dumps(log_data))


def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )
