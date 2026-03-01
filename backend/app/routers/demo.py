"""
Demo seeding router.

POST /api/demo/seed   — compile 5 template components and store them for default-tenant.
GET  /api/demo/status — check whether demo components already exist.
"""

from fastapi import APIRouter, Request
import logging

from app.database import get_storage, get_redis
from app.middleware.auth import get_tenant_id
from app.services.compiler import ComponentCompiler
from app.services.template_engine import TemplateEngine
from app.component_library.templates import COMPONENT_TEMPLATES
import json

# Pre-shaped mock data keyed by template name so each component's `data`/`metrics`/`summary`
# props receive the right structure — not the raw generate_mock_dataset blob.
_TEMPLATE_MOCK_DATA: dict = {
    "MetricsDashboard": {
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
    },
    "LineChart": [
        {"date": "Jan", "value": 52400},
        {"date": "Feb", "value": 58900},
        {"date": "Mar", "value": 61200},
        {"date": "Apr", "value": 67800},
        {"date": "May", "value": 74200},
        {"date": "Jun", "value": 82100},
        {"date": "Jul", "value": 69800},
        {"date": "Aug", "value": 78300},
        {"date": "Sep", "value": 85600},
        {"date": "Oct", "value": 91200},
        {"date": "Nov", "value": 88400},
        {"date": "Dec", "value": 96100},
    ],
    "DataTable": [
        {"name": "Laptop Pro 15", "category": "Electronics", "price": 1499, "stock": 42, "rating": 4.7},
        {"name": "Wireless Headphones", "category": "Electronics", "price": 199, "stock": 128, "rating": 4.5},
        {"name": "Standing Desk", "category": "Furniture", "price": 399, "stock": 67, "rating": 4.6},
        {"name": "Ergonomic Chair", "category": "Furniture", "price": 349, "stock": 54, "rating": 4.8},
        {"name": "Mechanical Keyboard", "category": "Electronics", "price": 99, "stock": 215, "rating": 4.4},
        {"name": "4K Monitor", "category": "Electronics", "price": 599, "stock": 33, "rating": 4.6},
        {"name": "Running Shoes", "category": "Sports", "price": 99, "stock": 189, "rating": 4.3},
        {"name": "Yoga Mat", "category": "Sports", "price": 29, "stock": 402, "rating": 4.5},
        {"name": "Coffee Maker", "category": "Kitchen", "price": 149, "stock": 97, "rating": 4.4},
        {"name": "Blender Pro", "category": "Kitchen", "price": 99, "stock": 134, "rating": 4.2},
    ],
    "PieChart": [
        {"name": "Electronics", "value": 330700},
        {"name": "Furniture", "value": 148500},
        {"name": "Sports", "value": 67100},
        {"name": "Kitchen", "value": 68500},
        {"name": "Other", "value": 232520},
    ],
    "StatCard": [
        {"title": "Revenue", "value": 847320, "trend": "+18.4%"},
        {"title": "Orders", "value": 4312, "trend": "+12.1%"},
        {"title": "MRR", "value": 70610, "trend": "+9.8%"},
        {"title": "New Customers", "value": 1842, "trend": "+7.3%"},
    ],
    "BarChart": [
        {"name": "Electronics", "value": 330700},
        {"name": "Furniture", "value": 148500},
        {"name": "Sports", "value": 67100},
        {"name": "Kitchen", "value": 68500},
        {"name": "Other", "value": 232520},
    ],
    "AreaChart": [
        {"date": "Jan", "value": 52400},
        {"date": "Feb", "value": 58900},
        {"date": "Mar", "value": 61200},
        {"date": "Apr", "value": 67800},
        {"date": "May", "value": 74200},
        {"date": "Jun", "value": 82100},
    ],
    "ComposedChart": [
        {"date": "Jan", "lineValue": 52400, "barValue": 267},
        {"date": "Feb", "lineValue": 58900, "barValue": 301},
        {"date": "Mar", "lineValue": 61200, "barValue": 318},
        {"date": "Apr", "lineValue": 67800, "barValue": 345},
        {"date": "May", "lineValue": 74200, "barValue": 379},
        {"date": "Jun", "lineValue": 82100, "barValue": 420},
    ],
    "ListWithSearch": [
        {"name": "Laptop Pro 15", "category": "Electronics", "price": 1499, "stock": 42},
        {"name": "Wireless Headphones", "category": "Electronics", "price": 199, "stock": 128},
        {"name": "Standing Desk", "category": "Furniture", "price": 399, "stock": 67},
        {"name": "Ergonomic Chair", "category": "Furniture", "price": 349, "stock": 54},
        {"name": "Mechanical Keyboard", "category": "Electronics", "price": 99, "stock": 215},
        {"name": "Running Shoes", "category": "Sports", "price": 99, "stock": 189},
        {"name": "Coffee Maker", "category": "Kitchen", "price": 149, "stock": 97},
    ],
}

logger = logging.getLogger(__name__)
router = APIRouter()

DEMO_TENANT = "default-tenant"
DEMO_USER = "demo-seed"

# (template_name, prompt, display_name)
DEMO_DEFINITIONS = [
    (
        "MetricsDashboard",
        "Show me a sales metrics dashboard with revenue and orders",
        "Sales Overview Dashboard",
        "ecommerce",
    ),
    (
        "LineChart",
        "Show monthly revenue trend for ecommerce",
        "Monthly Revenue Trend",
        "ecommerce",
    ),
    (
        "DataTable",
        "Show me a product catalog table",
        "Product Catalog",
        "ecommerce",
    ),
    (
        "PieChart",
        "Revenue breakdown by category",
        "Revenue by Category",
        "ecommerce",
    ),
    (
        "StatCard",
        "Show me SaaS KPI metrics with MRR and churn",
        "SaaS KPI Cards",
        "saas",
    ),
]


async def _seed_demo_components(tenant_id: str) -> dict:
    """Compile and store all demo components. Idempotent — skips already-seeded components."""
    storage = get_storage()
    redis = await get_redis()
    compiler = ComponentCompiler()
    engine = TemplateEngine()

    # Fetch already-seeded component names so we skip duplicates
    existing = await storage.list_components(tenant_id, limit=100, status="active")
    existing_names = {c["name"] for c in existing["components"]}

    created = []
    skipped = []
    errors = []

    for tpl_name, prompt, display_name, profile in DEMO_DEFINITIONS:
        if display_name in existing_names:
            skipped.append(display_name)
            continue

        template = COMPONENT_TEMPLATES.get(tpl_name)
        if not template:
            errors.append(f"{tpl_name}: template not found")
            continue

        try:
            code = engine.fill_template(template, prompt)
            code_hash = ComponentCompiler.compute_hash(code)
            result = await compiler.compile(code, code_hash)

            if not result.success:
                errors.append(f"{display_name}: {result.error}")
                continue

            component_id = await storage.create_component({
                "tenant_id": tenant_id,
                "user_id": DEMO_USER,
                "name": display_name,
                "description": f"Demo component — {template.description}",
                "solidjs_code": code,
                "compiled_bundle": result.bundle,
                "bundle_size_bytes": result.bundle_size,
                "code_hash": code_hash,
                "status": "active",
                "version": "1.0.0",
            })

            # Inject shaped mock data into Redis so the Data Bridge "Real" toggle works.
            # Use the template-specific shape so the component's `data` prop gets
            # the right structure (array vs {metrics, summary} object).
            if redis:
                real_data = _TEMPLATE_MOCK_DATA.get(tpl_name, _TEMPLATE_MOCK_DATA.get("DataTable"))
                cache_key = f"databridge:{tenant_id}:{component_id}:real"
                await redis.setex(cache_key, 86400 * 30, json.dumps(real_data))

            created.append({"id": component_id, "name": display_name})
            logger.info(f"Demo seeded: {display_name} ({component_id})")

        except Exception as exc:
            logger.error(f"Failed to seed {display_name}: {exc}")
            errors.append(f"{display_name}: {exc}")

    return {"created": created, "skipped": skipped, "errors": errors}


@router.get("/status")
async def demo_status(request: Request):
    """Check whether demo components have been seeded."""
    tenant_id = get_tenant_id(request)
    storage = get_storage()
    result = await storage.list_components(tenant_id, limit=100, status="active")
    demo_names = {d[2] for d in DEMO_DEFINITIONS}  # display names
    existing = {c["name"] for c in result["components"]}
    seeded = demo_names & existing
    return {
        "seeded": len(seeded) > 0,
        "count": len(seeded),
        "total": len(DEMO_DEFINITIONS),
        "components": [c for c in result["components"] if c["name"] in demo_names],
    }


@router.post("/seed")
async def seed_demo(request: Request):
    """
    Compile and store demo components for the current tenant.
    Safe to call multiple times — already-seeded components are skipped.
    """
    tenant_id = get_tenant_id(request)
    result = await _seed_demo_components(tenant_id)
    return {
        "status": "ok" if not result["errors"] else "partial",
        **result,
    }
