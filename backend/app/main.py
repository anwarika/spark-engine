from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app import __version__
from app.config import settings
from app.database import close_connections
from app.middleware.auth import AuthMiddleware, set_storage as auth_set_storage
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import StructuredLoggingMiddleware, setup_logging
from app.routers import chat, components, health, mock, catalog, a2a, cag_admin, apps, dashboards, keys, admin, transform


setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inject storage into auth middleware so API key lookups work
    from app.database import get_storage
    auth_set_storage(get_storage())
    yield
    await close_connections()


app = FastAPI(
    title="Spark API",
    description="AI-Powered Micro App Generation Service",
    version=__version__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(components.router, prefix="/api/components", tags=["components"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["catalog"])
app.include_router(mock.router, prefix="/api", tags=["mock"])
app.include_router(a2a.router, prefix="/api/a2a", tags=["a2a"])
app.include_router(cag_admin.router, prefix="/api", tags=["cag"])
app.include_router(apps.router, prefix="/api/apps", tags=["apps"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(keys.router, prefix="/api/keys", tags=["keys"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(transform.router, prefix="/api", tags=["transform"])

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    # Serve agent.json specifically
    @app.get("/.well-known/agent.json")
    async def serve_agent_json():
        agent_path = os.path.join(static_dir, "agent.json")
        if os.path.exists(agent_path):
            return FileResponse(agent_path, media_type="application/json")
        return {"error": "Agent metadata not found"}

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith(".well-known/"):
            return {"error": "Not found"}

        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        return FileResponse(os.path.join(static_dir, "index.html"))
