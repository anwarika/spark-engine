import logging
import json
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(time.time()))

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "tenant_id": getattr(request.state, "tenant_id", None),
            "user_id": getattr(request.state, "user_id", None)
        }

        try:
            response = await call_next(request)

            execution_time = (time.time() - start_time) * 1000
            log_data.update({
                "status_code": response.status_code,
                "execution_time_ms": round(execution_time, 2)
            })

            logging.info(json.dumps(log_data))

            return response
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            log_data.update({
                "status_code": 500,
                "execution_time_ms": round(execution_time, 2),
                "error": str(e)
            })
            logging.error(json.dumps(log_data))
            raise


def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )
