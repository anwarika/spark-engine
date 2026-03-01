"""Component catalog/templates router for saving and reusing components."""

from fastapi import APIRouter, Request, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
from app.services.compiler import ComponentCompiler
from app.component_library.templates import list_templates as list_builtin_templates

logger = logging.getLogger(__name__)
router = APIRouter()


class SaveTemplateRequest(BaseModel):
    """Request to save a component as a template."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = "custom"
    tags: Optional[List[str]] = None
    react_code: str
    is_public: Optional[bool] = False


class PreviewRequest(BaseModel):
    """Request to preview a React component by compiling and returning iframe HTML."""
    react_code: str


class UseTemplateRequest(BaseModel):
    """Request to use a template (increments usage count)."""
    template_id: str


# Shared mock data injected into every template preview.
# Fields cover all template prop shapes simultaneously:
#   data[]         → DataTable, ListWithSearch, BarChart, PieChart, LineChart,
#                    AreaChart, ComposedChart (picks whichever key it needs)
#   data[].title   → StatCard KPI label
#   data[].value   → numeric value for all chart types
#   data[].trend   → StatCard trend badge
#   data[].date    → time-series x-axis
#   data[].name    → bar/pie label
#   metrics[]      → MetricsDashboard trend chart
#   summary{}      → MetricsDashboard stats tiles
_PREVIEW_MOCK_DATA = {
    "data": [
        {
            "name": "Revenue", "title": "Revenue", "category": "Ecommerce",
            "date": "Jan", "value": 247000,
            "lineValue": 247000, "barValue": 1234,
            "price": 847, "stock": 42, "trend": "+18%",
        },
        {
            "name": "Orders", "title": "Orders", "category": "Ecommerce",
            "date": "Feb", "value": 312000,
            "lineValue": 312000, "barValue": 1567,
            "price": 199, "stock": 128, "trend": "+12%",
        },
        {
            "name": "Customers", "title": "New Customers", "category": "SaaS",
            "date": "Mar", "value": 189000,
            "lineValue": 189000, "barValue": 945,
            "price": 399, "stock": 67, "trend": "+9%",
        },
        {
            "name": "MRR", "title": "MRR", "category": "SaaS",
            "date": "Apr", "value": 99320,
            "lineValue": 99320, "barValue": 497,
            "price": 149, "stock": 215,
        },
        {
            "name": "Churn", "title": "Churn Rate", "category": "SaaS",
            "date": "May", "value": 42100,
            "lineValue": 42100, "barValue": 211,
            "price": 99, "stock": 33,
        },
        {
            "name": "ARR", "title": "ARR", "category": "Finance",
            "date": "Jun", "value": 74200,
            "lineValue": 74200, "barValue": 379,
            "price": 599, "stock": 189,
        },
    ],
    "metrics": [
        {"date": "Jan", "value": 52400, "lineValue": 52400, "barValue": 267},
        {"date": "Feb", "value": 58900, "lineValue": 58900, "barValue": 301},
        {"date": "Mar", "value": 61200, "lineValue": 61200, "barValue": 318},
        {"date": "Apr", "value": 67800, "lineValue": 67800, "barValue": 345},
        {"date": "May", "value": 74200, "lineValue": 74200, "barValue": 379},
        {"date": "Jun", "value": 82100, "lineValue": 82100, "barValue": 420},
    ],
    "summary": {
        "total_revenue": 847320,
        "total_orders": 4312,
        "mrr": 70610,
        "arr": 847320,
    },
}


def _build_preview_iframe_html(request: Request, bundle: str, mock_data: dict | None = None) -> str:
    """Build iframe HTML with inlined compiled bundle and optional mock data for preview."""
    import json as _json
    base_url = str(request.base_url).rstrip("/")
    safe_bundle = bundle.replace("</script>", "<\\/script>")
    data_script = ""
    if mock_data:
        safe_json = _json.dumps(mock_data)
        data_script = f"window.__PREVIEW_DATA = {safe_json};"
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spark Preview</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --background: 240 10% 3.9%;
      --foreground: 0 0% 98%;
      --card: 240 10% 3.9%;
      --card-foreground: 0 0% 98%;
      --primary: 0 0% 98%;
      --primary-foreground: 0 0% 9%;
      --secondary: 0 0% 14.9%;
      --secondary-foreground: 0 0% 98%;
      --muted: 0 0% 14.9%;
      --muted-foreground: 0 0% 63.9%;
      --accent: 0 0% 14.9%;
      --accent-foreground: 0 0% 98%;
      --destructive: 0 62.8% 30.6%;
      --destructive-foreground: 0 0% 98%;
      --border: 0 0% 14.9%;
      --input: 0 0% 14.9%;
      --ring: 0 0% 83.1%;
      --radius: 0.5rem;
      --chart-1: 220 70% 50%;
      --chart-2: 160 60% 45%;
      --chart-3: 30 80% 55%;
      --chart-4: 280 65% 60%;
      --chart-5: 340 75% 55%;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, sans-serif;
      min-height: 100vh;
      background-color: hsl(var(--background));
      color: hsl(var(--foreground));
    }}
  </style>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/recharts@2/umd/Recharts.min.js"></script>
  <script src="{base_url}/api/static/shadcn-ui-bundle.js"></script>
  <script src="https://unpkg.com/lucide-react/dist/umd/lucide-react.js"></script>
  <script>window.LucideReact = window.LucideReact || window.lucideReact || window.lucide || {{}};</script>
</head>
<body>
  <div id="root"></div>
  <script>
    window.__DATA_MODE = 'sample';
    {data_script}
    window.onerror = function(msg, url, line, col, error) {{
      console.error('Error:', msg, 'at', url, line, col, error);
      var root = document.getElementById('root');
      if (root) root.innerHTML = '<div style="padding: 20px; color: red;">Error: ' + msg + '</div>';
      return false;
    }};
    window.addEventListener('unhandledrejection', function(e) {{ console.error('Unhandled rejection:', e.reason); }});
  </script>
  <script>{safe_bundle}</script>
  <script>
    try {{
      var SparkComponent = window.SparkComponent;
      if (!SparkComponent || !SparkComponent.default) {{
        throw new Error('Component failed to load');
      }}
      var rootEl = document.getElementById('root');
      var root = ReactDOM.createRoot(rootEl);
      // Spread all keys from __PREVIEW_DATA so every template prop shape is covered:
      //   data[]    → DataTable / charts / ListWithSearch / StatCard
      //   metrics[] → MetricsDashboard trend chart
      //   summary   → MetricsDashboard stat tiles
      var previewProps = window.__PREVIEW_DATA || null;
      root.render(React.createElement(SparkComponent.default, previewProps));
      window.addEventListener('message', function(event) {{
        if (event.data && event.data.type === 'spark_data') {{
          root.render(React.createElement(SparkComponent.default, {{ data: event.data.payload }}));
        }}
        if (event.data && event.data.type === 'spark_theme') {{
          document.documentElement.classList.toggle('dark', event.data.theme === 'dark');
        }}
        if (event.data && event.data.type === 'data_swap') {{
          root.render(React.createElement(SparkComponent.default, {{ data: event.data.data }}));
        }}
      }});
    }} catch (error) {{
      console.error('Failed to render:', error);
      document.getElementById('root').innerHTML = '<div style="padding: 20px; color: red;">' + error.message + '</div>';
    }}
  </script>
</body>
</html>"""


@router.get("/built-in-templates")
async def get_builtin_templates(
    request: Request,
    category: Optional[str] = None,
):
    """List built-in component templates (from templates.py). No DB required."""
    templates = list_builtin_templates(category=category)
    return {
        "templates": [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "tags": t.tags,
                "data_requirements": t.data_requirements,
                "code": t.code,
            }
            for t in templates
        ]
    }


@router.post("/preview")
async def preview_component(request: Request, body: PreviewRequest):
    """
    Compile React code and return iframe HTML for live preview.
    Frontend uses response as blob URL or srcdoc for iframe.
    """
    compiler = ComponentCompiler()
    code_hash = ComponentCompiler.compute_hash(body.react_code)
    result = await compiler.compile(body.react_code, code_hash)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Compilation failed")

    html = _build_preview_iframe_html(request, result.bundle, mock_data=_PREVIEW_MOCK_DATA)
    return Response(content=html, media_type="text/html")


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
    code_hash = ComponentCompiler.compute_hash(body.react_code)

    # Optional: compile the template to store compiled bundle
    compiler = ComponentCompiler()
    compilation_result = await compiler.compile(body.react_code, code_hash)
    
    compiled_bundle = None
    bundle_size = None
    if compilation_result.success:
        compiled_bundle = compilation_result.bundle
        bundle_size = compilation_result.bundle_size

    # Save to database (storage uses solidjs_code column for backward compat)
    data = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "name": body.name,
        "description": body.description,
        "category": body.category,
        "tags": body.tags or [],
        "solidjs_code": body.react_code,
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
    Returns the template's React code for generation.
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
        "react_code": template["solidjs_code"],
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
