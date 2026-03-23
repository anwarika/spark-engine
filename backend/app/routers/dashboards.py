"""
/api/dashboards — persisted dashboard canvas layouts (grid items keyed by pin_id).
"""
from fastapi import APIRouter, Request, HTTPException, Query
import logging

from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
from app.models import DashboardLayoutSaveRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_layout(layout: list) -> list:
    if not isinstance(layout, list):
        raise HTTPException(status_code=400, detail="layout must be a list")
    out = []
    for idx, item in enumerate(layout):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"layout[{idx}] must be an object")
        i = item.get("i")
        if not i or not isinstance(i, str):
            raise HTTPException(
                status_code=400, detail=f"layout[{idx}].i must be a non-empty string (pin id)"
            )
        try:
            x = int(item["x"])
            y = int(item["y"])
            w = int(item["w"])
            h = int(item["h"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"layout[{idx}] requires integer x, y, w, h",
            )
        if w < 1 or w > 24 or h < 1 or h > 50:
            raise HTTPException(
                status_code=400, detail="w must be 1-24, h must be 1-50",
            )
        cell = {"i": i, "x": x, "y": y, "w": w, "h": h}
        if item.get("minW") is not None:
            cell["minW"] = int(item["minW"])
        if item.get("minH") is not None:
            cell["minH"] = int(item["minH"])
        out.append(cell)
    return out


@router.get("/layout")
async def get_layout(
    request: Request,
    name: str = Query("default", min_length=1, max_length=120),
):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()
    row = await storage.get_dashboard_layout(tenant_id, user_id, name)
    if not row:
        return {"name": name, "layout": [], "updated_at": None}
    return {
        "name": row["name"],
        "layout": row.get("layout") or [],
        "updated_at": row.get("updated_at"),
    }


@router.put("/layout")
async def save_layout(request: Request, body: DashboardLayoutSaveRequest):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()
    clean = _validate_layout(body.layout)
    try:
        saved = await storage.upsert_dashboard_layout(
            tenant_id, user_id, body.name or "default", clean
        )
    except Exception as e:
        logger.exception("Failed to save dashboard layout: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save dashboard layout")
    return {
        "name": saved["name"],
        "layout": saved["layout"],
        "updated_at": saved.get("updated_at"),
    }
