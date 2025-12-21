"""Component catalog/templates router for saving and reusing components."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
from app.services.compiler import ComponentCompiler

logger = logging.getLogger(__name__)
router = APIRouter()


class SaveTemplateRequest(BaseModel):
    """Request to save a component as a template."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = "custom"
    tags: Optional[List[str]] = None
    solidjs_code: str
    is_public: Optional[bool] = False


class UseTemplateRequest(BaseModel):
    """Request to use a template (increments usage count)."""
    template_id: str


@router.get("/templates")
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """List available templates (own + public)."""
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    result = await storage.list_component_templates(
        tenant_id=tenant_id, 
        category=category, 
        is_public=is_public, 
        tag=tag, 
        limit=limit, 
        offset=offset
    )

    return {
        "templates": result["templates"],
        "total": result["total"],
        "limit": limit,
        "offset": offset
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str, request: Request):
    """Get a specific template by ID."""
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    template = await storage.get_component_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access: own template or public
    # Note: storage.get_component_template returns it regardless of tenant, 
    # we enforce access here.
    # Postgres returns strings for UUIDs, Supabase returns strings.
    template_tenant = str(template.get("tenant_id"))
    
    if template_tenant != tenant_id and not template.get("is_public", False):
        raise HTTPException(status_code=403, detail="Access denied")

    return template


@router.post("/templates")
async def save_template(request: Request, body: SaveTemplateRequest):
    """Save a component as a reusable template."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    # Compute code hash
    code_hash = ComponentCompiler.compute_hash(body.solidjs_code)

    # Optional: compile the template to store compiled bundle
    compiler = ComponentCompiler()
    compilation_result = await compiler.compile(body.solidjs_code, code_hash)
    
    compiled_bundle = None
    bundle_size = None
    if compilation_result.success:
        compiled_bundle = compilation_result.bundle
        bundle_size = compilation_result.bundle_size

    # Save to database
    data = {
        "tenant_id": tenant_id, # Storage might require this in args but good to have in data
        "user_id": user_id,
        "name": body.name,
        "description": body.description,
        "category": body.category,
        "tags": body.tags or [],
        "solidjs_code": body.solidjs_code,
        "code_hash": code_hash,
        "compiled_bundle": compiled_bundle,
        "bundle_size_bytes": bundle_size,
        "is_public": body.is_public
    }
    
    template = await storage.create_or_update_template(tenant_id, data)

    logger.info(f"Saved template: {body.name} (id={template.get('id')})")

    return {
        "status": "success",
        "template": template
    }


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str, request: Request):
    """
    Mark a template as used (increment usage count).
    Returns the template's SolidJS code for generation.
    """
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    # Get template
    template = await storage.get_component_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access
    template_tenant = str(template.get("tenant_id"))
    if template_tenant != tenant_id and not template.get("is_public", False):
        raise HTTPException(status_code=403, detail="Access denied")

    # Increment usage count
    await storage.increment_template_usage(template_id)

    return {
        "status": "success",
        "solidjs_code": template["solidjs_code"],
        "compiled_bundle": template.get("compiled_bundle"),
        "template": {
            "id": template["id"],
            "name": template["name"],
            "category": template["category"],
            "tags": template["tags"]
        }
    }


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, request: Request):
    """Delete a template (own templates only)."""
    tenant_id = get_tenant_id(request)
    storage = get_storage()

    # Verify ownership handled by storage.delete_template checking tenant_id condition?
    # No, storage.delete_template(template_id, tenant_id) enforces it.
    
    success = await storage.delete_template(template_id, tenant_id)

    if not success:
        # Could be not found or not owned.
        # Check existence first to give better error?
        # For now, generic 404 is okay or we check get_template first.
        # Let's trust storage returns false if nothing deleted.
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    logger.info(f"Deleted template: {template_id}")

    return {"status": "success"}


@router.get("/categories")
async def list_categories(request: Request):
    """List all available template categories."""
    return {
        "categories": [
            {"id": "chart", "name": "Charts", "description": "Line, bar, pie charts"},
            {"id": "table", "name": "Tables", "description": "Data tables with filtering and sorting"},
            {"id": "card", "name": "Cards", "description": "KPI cards and stat displays"},
            {"id": "dashboard", "name": "Dashboards", "description": "Multi-metric overviews"},
            {"id": "list", "name": "Lists", "description": "Searchable lists and directories"},
            {"id": "custom", "name": "Custom", "description": "Custom components"}
        ]
    }
