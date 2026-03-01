#!/usr/bin/env python3
"""
Seed the Spark app with demo components.

Usage (from repo root):
  docker-compose exec backend python scripts/seed_demo.py

Or locally (with DATABASE_URL + REDIS_URL in env):
  cd backend && python scripts/seed_demo.py [--tenant default-tenant] [--clear]

Flags:
  --tenant  Tenant ID to seed (default: default-tenant)
  --clear   Remove previously seeded demo components before re-seeding
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_storage, get_redis
from app.services.compiler import ComponentCompiler
from app.services.template_engine import TemplateEngine
from app.component_library.templates import COMPONENT_TEMPLATES
import json

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DEMO_USER = "demo-seed"

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


async def clear_demo(tenant_id: str):
    storage = get_storage()
    existing = await storage.list_components(tenant_id, limit=100, status="active")
    demo_names = {d[2] for d in DEMO_DEFINITIONS}
    removed = 0
    for comp in existing["components"]:
        if comp["name"] in demo_names:
            await storage.update_component_status(comp["id"], tenant_id, "archived")
            removed += 1
    logger.info(f"Archived {removed} existing demo component(s)")


async def seed(tenant_id: str):
    storage = get_storage()
    redis = await get_redis()
    compiler = ComponentCompiler()
    engine = TemplateEngine()

    existing = await storage.list_components(tenant_id, limit=100, status="active")
    existing_names = {c["name"] for c in existing["components"]}

    created = 0
    skipped = 0

    for tpl_name, prompt, display_name, profile in DEMO_DEFINITIONS:
        if display_name in existing_names:
            logger.info(f"  skip  {display_name} (already exists)")
            skipped += 1
            continue

        template = COMPONENT_TEMPLATES.get(tpl_name)
        if not template:
            logger.warning(f"  warn  template {tpl_name!r} not found — skipping")
            continue

        logger.info(f"  build {display_name} …")
        try:
            code = engine.fill_template(template, prompt)
            code_hash = ComponentCompiler.compute_hash(code)
            result = await compiler.compile(code, code_hash)

            if not result.success:
                logger.error(f"  fail  {display_name}: {result.error}")
                continue

            component_id = await storage.create_component({
                "tenant_id": tenant_id,
                "user_id": DEMO_USER,
                "name": display_name,
                "description": f"Demo — {template.description}",
                "solidjs_code": code,
                "compiled_bundle": result.bundle,
                "bundle_size_bytes": result.bundle_size,
                "code_hash": code_hash,
                "status": "active",
                "version": "1.0.0",
            })

            # Inject shaped mock data so the Real toggle shows the right structure.
            if redis:
                from app.routers.demo import _TEMPLATE_MOCK_DATA
                real_data = _TEMPLATE_MOCK_DATA.get(tpl_name, _TEMPLATE_MOCK_DATA.get("DataTable"))
                cache_key = f"databridge:{tenant_id}:{component_id}:real"
                await redis.setex(cache_key, 86400 * 30, json.dumps(real_data))
                logger.info(f"  data  injected shaped mock data for {tpl_name}")

            logger.info(f"  done  {display_name} → {component_id}")
            created += 1

        except Exception as exc:
            logger.exception(f"  fail  {display_name}: {exc}")

    logger.info("")
    logger.info(f"Seeding complete: {created} created, {skipped} skipped")
    return created


async def main():
    parser = argparse.ArgumentParser(description="Seed Spark demo data")
    parser.add_argument("--tenant", default="default-tenant", help="Tenant ID")
    parser.add_argument("--clear", action="store_true", help="Archive existing demo components first")
    args = parser.parse_args()

    logger.info(f"Seeding demo for tenant: {args.tenant}")

    if args.clear:
        logger.info("Clearing existing demo components…")
        await clear_demo(args.tenant)

    await seed(args.tenant)


if __name__ == "__main__":
    asyncio.run(main())
