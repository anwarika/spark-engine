from typing import Any, Dict, List, Optional
from app.models import ChatResponse
from app.config import settings
from app.services.prompt_cache import PromptCache
from app.services.llm_gateway import LLMGateway, LLMConfig
import logging
import json
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _config_from_settings() -> LLMConfig:
    """Build LLMConfig from application settings."""
    api_key = settings.llm_api_key
    if not api_key:
        provider_keys = {
            "openai": settings.openai_api_key,
            "openrouter": settings.openrouter_api_key,
            "litellm": settings.litellm_api_key,
            "llmgw": settings.llmgw_api_key,
            "custom": settings.custom_llm_api_key,
        }
        api_key = provider_keys.get(settings.llm_provider)

    model = settings.llm_model
    if settings.llm_provider == "openai" and settings.openai_model:
        model = settings.openai_model
    elif settings.llm_provider == "openrouter" and settings.openrouter_model:
        model = settings.openrouter_model

    base_url = settings.llm_base_url
    if not base_url and settings.llm_provider == "llmgw":
        base_url = settings.llmgw_base_url
    elif not base_url and settings.llm_provider == "custom":
        base_url = settings.custom_llm_base_url

    return LLMConfig(
        provider=settings.llm_provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
        fallback_provider=settings.llm_fallback_provider,
        fallback_model=settings.llm_fallback_model,
        fallback_api_key=settings.llm_fallback_api_key,
        fallback_base_url=settings.llm_fallback_base_url,
    )


class LLMService:
    def __init__(self):
        self.prompt_cache = PromptCache()
        default_config = _config_from_settings()
        self.gateway = LLMGateway(default_config)

        self.system_prompt = """You are an expert at generating microapps for end users.
You generate Spark native microapps: lightweight Solid.js micro-components for data visualization and interaction.

AVAILABLE PRE-BUILT TEMPLATES (use when appropriate for faster, optimized generation):
1. StatCard - KPI cards with trend indicators (for: metrics, kpis, summary stats)
2. DataTable - Filterable/sortable tables (for: listing data, tables, browsing records)
3. LineChart - Time series line charts (for: trends over time, line graphs)
4. BarChart - Comparison bar charts (for: comparing values, bar graphs)
5. ListWithSearch - Searchable lists (for: browsing items, directories)
6. MetricsDashboard - Multi-metric dashboard with area chart (for: dashboards, overviews, multiple KPIs)
7. DonutChart - Category breakdown donut/pie (for: distributions, breakdowns)
8. HeatmapChart - Time-series intensity heatmap (for: activity, intensity over time)
9. MixedChart - Combined line + bar chart (for: comparing two metrics)

WHEN TO USE TEMPLATES:
- User asks to "show", "display", "list", "chart" data → Use matching template
- Request mentions "dashboard", "overview", "metrics" → Use MetricsDashboard
- Request is for specific data visualization → Use corresponding chart template
- Templates are pre-optimized and compile faster than custom code

Guidelines for component generation:
1. Use Solid.js primitives: createSignal, createEffect, createResource, For, Show, Switch, onMount, onCleanup
2. Style primarily with DaisyUI classes (e.g., btn, card, table, badge, input) but you may combine them with Tailwind utilities
3. Components must be small, focused, and performant (target < 5KB compiled with templates, < 10KB custom)
4. Always export a default function component
5. Use createResource() to fetch data from API endpoints when possible
6. Keep state minimal and reactive using Solid.js primitives

Available libraries (import from CDN via importmap):
- ApexCharts: import ApexCharts from 'apexcharts'; use new ApexCharts(element, options); chart.render(); chart.destroy() on cleanup
- DaisyUI + Tailwind - for styling
- Helper utilities (formatters, aggregators) can be defined inline

FORBIDDEN APIs (will cause validation failure):
- NO window, document, localStorage, sessionStorage, indexedDB
- NO fetch, XMLHttpRequest, WebSocket (use createResource instead)
- NO eval, Function constructor
- NO setTimeout, setInterval (use createEffect with cleanup instead)
- NO importScripts, postMessage, parent, top, opener, location, navigator

For timing/delays: Use onMount() with onCleanup() for lifecycle, or createEffect() for reactive updates
For data fetching: ALWAYS prefer createResource() which handles async data properly

7. IMPORTANT: Use ES2015 syntax only - NO optional chaining (?.), NO nullish coalescing (??), NO private fields (#)

OPTIMIZATION RULES:
1. Prefer built-in templates when request matches a template pattern (faster, smaller bundles)
2. Match data profile to user domain: ecommerce, saas, marketing, finance, sales
3. Keep components focused and small (< 100 lines of code when possible)
4. Use DaisyUI classes - avoid custom CSS
5. Always use createResource for async data fetching

DATA PROFILE SELECTION (auto-detected but you can suggest):
- E-commerce: products, orders, customers → profile: 'ecommerce'
- SaaS: MRR, churn, retention, subscriptions → profile: 'saas'
- Marketing: campaigns, spend, leads, attribution → profile: 'marketing'
- Finance: P&L, revenue, expenses, transactions → profile: 'finance'
- Sales: pipeline, opportunities, deals, quota → profile: 'sales'

Decision guidance:
- Assess whether the user request matches a pre-built template pattern. If so, prefer template-based generation.
- For custom visualizations or unique UX requirements, generate custom components.
- If the query is purely conversational or explanatory, respond with text.
- When you choose to return a component, include reasoning for why a visual representation was preferable and which approach you chose.

Response format (IMPORTANT: Return raw code in the content field, NO markdown code fences):
{
  "type": "text" or "component",
  "content": "<your response or raw Solid.js code WITHOUT markdown fences>",
  "reasoning": "<brief explanation of your choice>"
}

MOCK DATA AVAILABLE:
Components MUST fetch data from: /api/components/{component_id}/data (POST request)
Use window.__COMPONENT_ID which is automatically available in the component environment.

IMPORTANT:
- If you want profile saas/marketing/finance/sales, you MUST include it in the POST body via body.mock.profile.
- If you do not send a body.mock.profile, the backend will return the default ecommerce-shaped dataset.

For larger datasets (latency/reactivity testing), pass this body:
{
  "mock": { "profile": "ecommerce|saas|marketing|finance|sales", "scale": "small|medium|large|xl", "seed": 1, "days": 180, "latency_ms": 0 }
}

The endpoint returns rich datasets in a single response.

PROFILE: ecommerce
- data.products: Array of products with id, name, category, price, stock, rating, status
- data.users: Array of users with id, name, email, role, status, joined
- data.sales: Array of sales records with id, date, product, quantity, revenue, region
- data.tasks: Array of tasks with id, title, assignee, status, priority, due
- data.metrics: Array of daily metrics with date, pageviews, users, revenue, conversions
- data.orders: Array of orders with id, customer, items, total, status, date
- data.order_items: Array of order line items with order_id, product_id, product, category, quantity, unit_price, revenue
- data.summary: Object with total_revenue, total_orders, active_users, avg_order_value, top_product, growth_rate

PROFILE: saas (revenue/retention)
- data.plans, data.accounts, data.users, data.subscriptions, data.subscription_events, data.invoices, data.payments, data.events
- data.metrics: daily series with mrr/arr/signups/trials/activations/churned_accounts/active_accounts
- data.kpi_monthly: monthly series with mrr/arr/net_new_mrr/churn_rate/gross_retention/net_retention

PROFILE: marketing (attribution)
- data.campaigns, data.ad_groups, data.ads, data.ad_spend_daily, data.leads, data.touchpoints, data.attribution
- data.metrics: daily series with spend/impressions/clicks/leads/opportunities/cpc/cpl

PROFILE: finance (P&L)
- data.gl_accounts, data.vendors, data.customers, data.invoices, data.transactions
- data.pnl_monthly: monthly P&L rollups (revenue/cogs/opex/gross_profit/gross_margin/ebitda)
- data.metrics: daily revenue/cogs/opex/gross_profit

PROFILE: sales (pipeline)
- data.reps, data.accounts, data.contacts, data.opportunities, data.opportunity_stage_history, data.activities, data.bookings, data.quota_monthly
- data.metrics: daily pipeline snapshot (open_opps/pipeline_amount/weighted_pipeline/bookings)

Example component with data fetching (REQUIRED PATTERN):

import { createSignal, createResource, For, Show } from 'solid-js';

async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: 'saas', scale: 'large', seed: 42, days: 365 }, data_mode: dataMode })
  });
  return response.json();
}

export default function ProductList() {
  const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  const [filter, setFilter] = createSignal('');

  const filteredProducts = () => {
    if (!apiData() || !apiData().products) return [];
    const f = filter().toLowerCase();
    if (!f) return apiData().products;
    return apiData().products.filter(function(p) {
      return p.name.toLowerCase().includes(f) || p.category.toLowerCase().includes(f);
    });
  };

  return (
    <div class="p-4">
      <h2 class="text-2xl font-bold mb-4">Product Catalog</h2>
      <input
        type="text"
        class="input input-bordered w-full mb-4"
        placeholder="Search products..."
        value={filter()}
        onInput={(e) => setFilter(e.target.value)}
      />
      <Show when={!apiData.loading} fallback={<div class="loading loading-spinner"></div>}>
        <div class="grid gap-4">
          <For each={filteredProducts()}>
            {function(product) {
              return (
                <div class="card bg-base-100 shadow">
                  <div class="card-body">
                    <h3 class="card-title">{product.name}</h3>
                    <div class="flex gap-2">
                      <span class="badge badge-secondary">{product.category}</span>
                      <span class="badge badge-accent">${product.price}</span>
                      <span class="badge">{product.stock} in stock</span>
                    </div>
                  </div>
                </div>
              );
            }}
          </For>
        </div>
      </Show>
    </div>
  );
}

Example with ApexCharts (import ApexCharts from 'apexcharts'):

import { createResource, createEffect, onCleanup } from 'solid-js';
import ApexCharts from 'apexcharts';

async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: 'ecommerce', scale: 'large', days: 90 }, data_mode: dataMode })
  });
  return response.json();
}

export default function RevenueChart() {
  const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  let chartRef;
  let chartInstance;

  createEffect(function() {
    if (!apiData() || !apiData().metrics || !chartRef) return;
    const metrics = apiData().metrics;
    const options = {
      chart: { type: 'line', toolbar: { show: false } },
      stroke: { curve: 'smooth', width: 2 },
      series: [{ name: 'Revenue', data: metrics.map(function(m) { return m.revenue; }) }],
      xaxis: { categories: metrics.map(function(m) { return m.date; }) },
      yaxis: { min: 0 }
    };
    if (chartInstance) chartInstance.destroy();
    chartInstance = new ApexCharts(chartRef, options);
    chartInstance.render();
  });

  onCleanup(function() {
    if (chartInstance) chartInstance.destroy();
  });

  return (
    <div class="p-6">
      <h2 class="text-2xl font-bold mb-4">Revenue Trend</h2>
      <div ref={chartRef} style="height: 400px;"></div>
    </div>
  );
}

DATA BRIDGE (sample to real swap):
- window.__DATA_MODE is 'sample' by default. Parent can postMessage { type: 'data_swap', mode: 'real' } to switch.
- Include data_mode in fetch body. Use createResource(source, fetchData) with source = function() { return window.__DATA_MODE; } so refetch triggers on mode change.
- Real data: POST to /api/components/{id}/data/swap with { mode: 'real', data: {...} } before switching.

Respond only with valid JSON in the specified format. CRITICAL: Do NOT wrap code in markdown fences."""
        self.style_doc_path = Path(__file__).resolve().parents[1] / "static" / "daisyui.txt"
        self._style_doc_content = ""
        self._style_doc_mtime = 0.0
        self._style_cache_max_length = 8000

    def _strip_markdown_fences(self, content: str) -> str:
        """Remove markdown code fences from content."""
        content = re.sub(r'^```[\w]*\n?', '', content.strip(), flags=re.MULTILINE)
        content = re.sub(r'\n?```$', '', content.strip(), flags=re.MULTILINE)
        return content.strip()

    def _refresh_style_reference(self):
        if not self.style_doc_path.exists():
            return
        try:
            mtime = self.style_doc_path.stat().st_mtime
        except OSError:
            return
        if mtime == self._style_doc_mtime:
            return
        try:
            content = self.style_doc_path.read_text(encoding="utf-8")
        except OSError:
            return
        self._style_doc_content = content
        self._style_doc_mtime = mtime

    def _get_style_reference_snippet(self) -> str:
        if not self._style_doc_content:
            return ""
        snippet = self._style_doc_content
        if len(snippet) > self._style_cache_max_length:
            snippet = snippet[:self._style_cache_max_length]
            snippet += "\n... (truncated; see backend/static/daisyui.txt for the full reference)"
        return snippet

    async def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        llm_config: Optional[LLMConfig] = None,
    ) -> ChatResponse:
        if conversation_history is None:
            conversation_history = []

        gateway = LLMGateway(llm_config) if llm_config else self.gateway

        # Check prompt cache first
        cached_response = await self.prompt_cache.get_cached_response(user_message, "general")
        if cached_response:
            logger.info("Using cached LLM response")
            return cached_response

        self._refresh_style_reference()
        style_snippet = self._get_style_reference_snippet()
        system_prompt = self.system_prompt
        if style_snippet:
            system_prompt = f"{system_prompt}\n\nDaisyUI reference (cached):\n{style_snippet}"

        messages = (
            [{"role": "system", "content": system_prompt}]
            + conversation_history
            + [{"role": "user", "content": user_message}]
        )

        try:
            completion = await gateway.chat(
                messages,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            parsed = json.loads(content)
            response = ChatResponse(
                type=parsed.get("type", "text"),
                content=parsed.get("content", ""),
                reasoning=parsed.get("reasoning", ""),
            )

            if response.type == "component":
                response.content = self._strip_markdown_fences(response.content)

            await self.prompt_cache.cache_response(user_message, "general", response)
            return response

        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return ChatResponse(
                type="text",
                content=f"I apologize, but I encountered an error: {str(e)}",
                reasoning="Error fallback",
            )

    # Delimiter used to extract the schema block from the main system prompt
    _SCHEMA_START_MARKER = "MOCK DATA AVAILABLE:"
    _SCHEMA_END_MARKER = "DATA BRIDGE (sample to real swap):"

    _EDIT_PROMPT_TEMPLATE = """You are editing an existing Solid.js microapp component. The user wants you to apply a specific change.

CURRENT COMPONENT CODE:
```solidjs
<<<EXISTING_CODE>>>
```

USER'S EDIT REQUEST:
<<<EDIT_INSTRUCTION>>>

FIELDS ALREADY USED IN THE CURRENT CODE (safe to reuse — prefer these over inventing new ones):
<<<EXISTING_FIELDS>>>

VALID DATA SCHEMA (use ONLY these field paths when accessing apiData() — do NOT invent field names):
<<<DATA_SCHEMA>>>

TASK:
1. Apply ONLY the change the user requested. Do not add unrelated features or refactor other parts.
2. Return the COMPLETE updated component code (full file) — do not return a diff or partial snippet.
3. PRESERVE all existing sections, layout, and behaviour when the user asks to "add" something — add without removing.
4. For layout changes, use Tailwind grid (grid grid-cols-2 gap-4, grid-cols-3), flex, and DaisyUI stat/card components.
5. Same rules as generation: Solid.js only, createResource for data, no window/fetch/eval, ES2015 syntax only.
6. CRITICAL: When accessing data fields, always use the exact snake_case paths listed in VALID DATA SCHEMA above.
   Example: use apiData().summary.total_revenue NOT apiData().totalRevenue
7. Guard every data access: if (!apiData() || !apiData().summary) return null;

Response format (JSON only, no markdown fences):
{
  "type": "component",
  "content": "<complete Solid.js component code>",
  "reasoning": "<brief note on what you changed>"
}"""

    def _extract_schema_section(self) -> str:
        """Pull the MOCK DATA AVAILABLE block from the main system prompt."""
        start = self.system_prompt.find(self._SCHEMA_START_MARKER)
        end = self.system_prompt.find(self._SCHEMA_END_MARKER)
        if start == -1 or end == -1 or end <= start:
            return "(schema not available)"
        return self.system_prompt[start:end].strip()

    def _extract_existing_fields(self, code: str) -> str:
        """Scan existing code for apiData() property accesses and return a bullet list."""
        # Matches patterns like: apiData().summary.total_revenue, apiData().metrics, etc.
        raw_matches = re.findall(r'apiData\(\)(?:\.\w+)+', code)
        if not raw_matches:
            return "(no existing apiData accesses found)"
        unique_sorted = sorted(set(raw_matches))
        return "\n".join(f"  - {m}" for m in unique_sorted)

    async def generate_edit_response(
        self,
        edit_instruction: str,
        existing_code: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        llm_config: Optional[LLMConfig] = None,
        prior_error: Optional[str] = None,
    ) -> ChatResponse:
        """Generate an edited component from user instruction and existing code.

        Args:
            prior_error: If set, this is a retry — inject the previous failure
                         into the instruction so the LLM can self-correct.
        """
        if conversation_history is None:
            conversation_history = []

        gateway = LLMGateway(llm_config) if llm_config else self.gateway

        self._refresh_style_reference()
        style_snippet = self._get_style_reference_snippet()

        # Fix 3: anchor to fields already present in the code
        existing_fields = self._extract_existing_fields(existing_code)
        # Fix 1: inject full data schema
        data_schema = self._extract_schema_section()

        effective_instruction = edit_instruction
        if prior_error:
            effective_instruction = (
                f"{edit_instruction}\n\n"
                f"IMPORTANT — your previous attempt produced this error, fix it:\n{prior_error}"
            )

        system_prompt = (
            self._EDIT_PROMPT_TEMPLATE
            .replace("<<<EXISTING_CODE>>>", existing_code)
            .replace("<<<EDIT_INSTRUCTION>>>", effective_instruction)
            .replace("<<<EXISTING_FIELDS>>>", existing_fields)
            .replace("<<<DATA_SCHEMA>>>", data_schema)
        )
        if style_snippet:
            system_prompt = f"{system_prompt}\n\nDaisyUI reference (cached):\n{style_snippet}"

        messages = (
            [{"role": "system", "content": system_prompt}]
            + conversation_history
            + [{"role": "user", "content": effective_instruction}]
        )

        try:
            completion = await gateway.chat(
                messages,
                response_format={"type": "json_object"},
                temperature=0.15,  # Fix 2: deterministic edits
            )
            content = completion.choices[0].message.content
            parsed = json.loads(content)
            response = ChatResponse(
                type=parsed.get("type", "component"),
                content=parsed.get("content", ""),
                reasoning=parsed.get("reasoning", ""),
            )

            if response.type == "component":
                response.content = self._strip_markdown_fences(response.content)

            return response

        except Exception as e:
            logger.error(f"LLM edit error: {str(e)}")
            return ChatResponse(
                type="text",
                content=f"I apologize, but I encountered an error while editing: {str(e)}",
                reasoning="Edit error fallback",
            )

    @property
    def model(self) -> str:
        return self.gateway.config.model

    async def chat_raw(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        llm_config: Optional[LLMConfig] = None,
        **kwargs: Any,
    ) -> str:
        """
        Low-level chat for analysis or custom flows. Bypasses cache.
        Returns raw message content.
        """
        gateway = LLMGateway(llm_config) if llm_config else self.gateway
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        completion = await gateway.chat(full_messages, **kwargs)
        return completion.choices[0].message.content or ""
