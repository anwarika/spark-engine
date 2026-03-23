"""
/api/apps — Pinned Apps router.

Pinned apps are the user's stable "bookmarked" app slots. A pin has a stable
ID and slot_name that persists even when the underlying component is regenerated.
This is the foundation for the nav-bar bookmarks in any host chat application.
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional
import logging
import json
import datetime

from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
from app.models import (
    PinAppRequest, UpdatePinMetaRequest, UpdatePinComponentRequest, PinnedAppResponse
)
from app.services.llm import LLMService
from app.services.compiler import ComponentCompiler

logger = logging.getLogger(__name__)
router = APIRouter()

_llm_service = LLMService()
_compiler = ComponentCompiler()


def _build_iframe_url(request: Request, component_id: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/components/{component_id}/iframe"


def _enrich(pin: dict, request: Request) -> dict:
    """Attach the derived iframe_url to a pin dict."""
    pin["iframe_url"] = _build_iframe_url(request, pin["component_id"])
    return pin


# ------------------------------------------------------------------
# GET /api/apps — list all pinned apps for the authenticated user
# ------------------------------------------------------------------

@router.get("")
async def list_pinned_apps(request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    pins = await storage.list_pinned_apps(tenant_id, user_id)
    return {
        "pinned_apps": [_enrich(p, request) for p in pins],
        "total": len(pins),
    }


# ------------------------------------------------------------------
# POST /api/apps/pin — pin an existing component
# ------------------------------------------------------------------

@router.post("/pin", status_code=201)
async def pin_app(request: Request, body: PinAppRequest):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    # Verify component exists and belongs to this tenant
    component = await storage.get_component(str(body.component_id), tenant_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    data = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "component_id": str(body.component_id),
        "slot_name": body.slot_name,
        "description": body.description,
        "icon": body.icon,
        "sort_order": body.sort_order,
        "metadata": json.dumps(body.metadata),
    }

    try:
        pin = await storage.create_pinned_app(data)
    except Exception as e:
        err_str = str(e).lower()
        if "unique" in err_str or "duplicate" in err_str:
            raise HTTPException(
                status_code=409,
                detail=f"A pinned app with slot_name '{body.slot_name}' already exists for this user."
            )
        logger.error(f"Failed to create pinned app: {e}")
        raise HTTPException(status_code=500, detail="Failed to pin app")

    return _enrich(pin, request)


# ------------------------------------------------------------------
# GET /api/apps/{pin_id} — get a single pinned app
# ------------------------------------------------------------------

@router.get("/{pin_id}")
async def get_pinned_app(pin_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    pin = await storage.get_pinned_app(pin_id, tenant_id, user_id)
    if not pin:
        raise HTTPException(status_code=404, detail="Pinned app not found")

    return _enrich(pin, request)


# ------------------------------------------------------------------
# PATCH /api/apps/{pin_id} — update label, icon, order, metadata
# ------------------------------------------------------------------

@router.patch("/{pin_id}")
async def update_pin_meta(pin_id: str, request: Request, body: UpdatePinMetaRequest):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    ok = await storage.update_pinned_app_meta(pin_id, tenant_id, user_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Pinned app not found")

    pin = await storage.get_pinned_app(pin_id, tenant_id, user_id)
    return _enrich(pin, request)


# ------------------------------------------------------------------
# POST /api/apps/{pin_id}/regenerate — re-generate component under pin
# ------------------------------------------------------------------

@router.post("/{pin_id}/regenerate")
async def regenerate_pinned_app(pin_id: str, request: Request, body: UpdatePinComponentRequest):
    """
    Re-generate the component behind a pin. The pin identity (id, slot_name,
    iframe URL via pin_id) remains stable — only component_id is swapped.

    If `prompt` is omitted, the original prompt stored in the component's
    description metadata is reused.
    """
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    pin = await storage.get_pinned_app(pin_id, tenant_id, user_id)
    if not pin:
        raise HTTPException(status_code=404, detail="Pinned app not found")

    existing = await storage.get_component(pin["component_id"], tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Underlying component not found")

    # Resolve the prompt to use
    prompt = body.prompt
    if not prompt:
        try:
            desc = json.loads(existing.get("description", "{}"))
            prompt = desc.get("prompt", "")
        except (json.JSONDecodeError, TypeError):
            prompt = existing.get("description", "")

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="No prompt provided and no prompt found in existing component metadata."
        )

    # Build full prompt with optional context
    full_prompt = prompt
    if body.data_context:
        full_prompt += f"\nDATA CONTEXT: {json.dumps(body.data_context)}"

    # Generate new component code (iterate on the existing one for continuity)
    response = await _llm_service.generate_edit_response(
        full_prompt,
        existing["solidjs_code"],
    )
    if response.type != "component":
        raise HTTPException(status_code=422, detail=f"LLM did not return a component: {response.content}")

    code_hash = ComponentCompiler.compute_hash(response.content)
    compilation = await _compiler.compile(response.content, code_hash)
    if not compilation.success:
        raise HTTPException(status_code=422, detail=f"Compilation failed: {compilation.error}")

    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    description_meta = json.dumps({
        "prompt": prompt,
        "source": "pin_regenerate",
        "parent_component_id": pin["component_id"],
        "pin_id": pin_id,
    })

    new_component_id = await storage.create_component({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "name": f"Pin-{pin['slot_name'][:30]}-{ts}",
        "description": description_meta,
        "solidjs_code": response.content,
        "code_hash": code_hash,
        "validated": True,
        "compiled": True,
        "compiled_bundle": compilation.bundle,
        "bundle_size_bytes": compilation.bundle_size,
        "status": "active",
    })

    # Atomic swap
    ok = await storage.update_pinned_app_component(
        pin_id, tenant_id, user_id, new_component_id,
        metadata={"last_regenerated_at": datetime.datetime.utcnow().isoformat()}
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to swap component under pin")

    updated_pin = await storage.get_pinned_app(pin_id, tenant_id, user_id)
    return {
        **_enrich(updated_pin, request),
        "previous_component_id": pin["component_id"],
        "new_component_id": new_component_id,
    }


# ------------------------------------------------------------------
# DELETE /api/apps/{pin_id} — unpin
# ------------------------------------------------------------------

@router.delete("/{pin_id}", status_code=204)
async def delete_pinned_app(pin_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    ok = await storage.delete_pinned_app(pin_id, tenant_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pinned app not found")
