# Contributing Component Templates

This guide explains how to add your own component library to Spark. Templates are React + shadcn/ui + Recharts components that the AI can use for rapid generation.

## Template Format

A template is defined by the `ComponentTemplate` dataclass:

```python
@dataclass
class ComponentTemplate:
    name: str           # e.g. "StatCard"
    category: str        # chart | table | card | dashboard | list | custom
    description: str    # Brief description for matching
    code: str           # Full React TSX source
    tags: List[str]     # Keywords for prompt matching, e.g. ["kpi", "metric"]
    data_requirements: List[str]  # Expected data fields, e.g. ["title", "value"]
```

## Adding a Template to `templates.py`

1. Define a `ComponentTemplate` instance with your React TSX code.
2. Add it to the `COMPONENT_TEMPLATES` dict:

```python
MY_TEMPLATE = ComponentTemplate(
    name="MyChart",
    category="chart",
    description="Custom chart for X",
    tags=["chart", "custom"],
    data_requirements=["label", "value"],
    code='''"use client"
import React from "react"
// ... your TSX ...
export default function MyChart({ data }: Props) { ... }
''',
)

COMPONENT_TEMPLATES["MyChart"] = MY_TEMPLATE
```

3. If your template uses placeholders for dynamic content, add a `_fill_my_chart` method in `app/services/template_engine.py` and register it in `fill_template()`.

## Placeholder Syntax

Templates use `{{PLACEHOLDER}}` for values filled by `TemplateEngine.fill_template()`:

- `{{TITLE_1}}`, `{{TITLE_2}}` — Stat card labels
- `{{CHART_TITLE}}`, `{{TABLE_TITLE}}`, `{{LIST_TITLE}}` — Section titles
- `{{DATE_FIELD}}`, `{{VALUE_FIELD}}` — Chart axis/field names
- `{{PROFILE}}` — Data profile (ecommerce, saas, sales, marketing, finance)

When adding a new template, add corresponding `_fill_*` logic in `template_engine.py` so placeholders are replaced based on the user prompt and detected data profile.

## Import Allowlist

The validator (`app/services/validator.py`) only allows these imports:

- `react`
- `react-dom`
- `recharts`
- `@/components/ui/*` (shadcn components)
- `lucide-react`

Your template must use only these. At runtime, `@/components/ui/*` resolves to the shadcn-ui bundle; `react`, `react-dom`, and `recharts` come from CDN globals.

## Adding via API

You can also add templates at runtime via the Sandbox UI or:

```bash
curl -X POST /api/catalog/templates \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default-tenant" \
  -H "X-User-ID: default-user" \
  -d '{
    "name": "MyTemplate",
    "category": "custom",
    "tags": ["custom"],
    "react_code": "YOUR_TSX_CODE_HERE"
  }'
```

Templates saved via API are stored in the database and available to your tenant. Built-in templates in `templates.py` are available to all tenants without DB storage.

## Custom Template Directory (Optional)

Set `CUSTOM_TEMPLATES_DIR` to a directory containing `*.py` files that define `ComponentTemplate` objects. These are auto-loaded and merged with built-in templates. See `load_custom_templates()` in `__init__.py`.
