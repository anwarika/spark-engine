"""Component catalog/templates router for saving and reusing components."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database import get_supabase
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
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    # Build query
    query = supabase.table("component_templates").select(
        "id, name, description, category, tags, code_hash, bundle_size_bytes, "
        "is_public, usage_count, created_at, updated_at"
    )

    # Apply filters
    if category:
        query = query.eq("category", category)
    
    if is_public is not None:
        query = query.eq("is_public", is_public)
    
    if tag:
        query = query.contains("tags", [tag])

    # Execute query with pagination
    result = query.order("usage_count", desc=True).range(offset, offset + limit - 1).execute()

    return {
        "templates": result.data,
        "total": len(result.data),
        "limit": limit,
        "offset": offset
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str, request: Request):
    """Get a specific template by ID."""
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    result = supabase.table("component_templates").select("*").eq("id", template_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")

    template = result.data[0]
    
    # Check access: own template or public
    if template["tenant_id"] != tenant_id and not template.get("is_public", False):
        raise HTTPException(status_code=403, detail="Access denied")

    return template


@router.post("/templates")
async def save_template(request: Request, body: SaveTemplateRequest):
    """Save a component as a reusable template."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

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
    result = supabase.table("component_templates").insert({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "name": body.name,
        "description": body.description,
        "category": body.category,
        "tags": body.tags or [],
        "solidjs_code": body.solidjs_code,
        "code_hash": code_hash,
        "compiled_bundle": compiled_bundle,
        "bundle_size_bytes": bundle_size,
        "is_public": body.is_public,
        "usage_count": 0
    }).execute()

    logger.info(f"Saved template: {body.name} (id={result.data[0]['id']})")

    return {
        "status": "success",
        "template": result.data[0]
    }


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str, request: Request):
    """
    Mark a template as used (increment usage count).
    Returns the template's SolidJS code for generation.
    """
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    # Get template
    result = supabase.table("component_templates").select("*").eq("id", template_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")

    template = result.data[0]
    
    # Check access
    if template["tenant_id"] != tenant_id and not template.get("is_public", False):
        raise HTTPException(status_code=403, detail="Access denied")

    # Increment usage count
    try:
        supabase.table("component_templates").update({
            "usage_count": template["usage_count"] + 1
        }).eq("id", template_id).execute()
    except Exception as e:
        logger.warning(f"Failed to increment usage count: {e}")

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
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    # Verify ownership
    result = supabase.table("component_templates").select("tenant_id").eq("id", template_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")

    if result.data[0]["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Can only delete own templates")

    # Delete
    supabase.table("component_templates").delete().eq("id", template_id).execute()

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

