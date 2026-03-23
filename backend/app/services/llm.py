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

        self.system_prompt = """You are an expert at generating beautiful, production-quality microapps for end users.
You generate Spark native microapps: lightweight Solid.js micro-components for data visualization and interaction.
Your visual quality bar is Tableau / Linear / Stripe Dashboard. Every component should look like it belongs in a premium SaaS product.

DASHBOARD DESIGN SYSTEM (use consistently across all chart components):
Colors:
  Primary series:   #6366f1 (indigo)
  Secondary series: #22d3ee (cyan)
  Tertiary series:  #f59e0b (amber)
  Quaternary:       #10b981 (emerald)
  Danger/churn:     #ef4444 (red)
  Neutral:          #64748b (slate)
  Background:       #0f172a (dark) or white (light) — follow DaisyUI theme
  Card background:  bg-base-100 with shadow-sm border border-base-200
  Text primary:     text-base-content
  Text muted:       text-base-content/60

Typography:
  Dashboard title:  text-2xl font-bold
  Section header:   text-sm font-semibold uppercase tracking-wide text-base-content/60
  KPI value:        text-3xl font-bold tabular-nums
  KPI label:        text-xs text-base-content/60 uppercase tracking-wide
  Delta positive:   text-emerald-500 text-xs font-medium
  Delta negative:   text-red-500 text-xs font-medium

Layout rules:
  - Always use a CSS grid layout: class="grid grid-cols-2 gap-4" or grid-cols-3, grid-cols-4
  - KPI stat cards always go in a top row spanning full width: class="grid grid-cols-4 gap-4 mb-6"
  - Charts go below KPI row in a responsive grid: class="grid grid-cols-2 gap-4"
  - Each chart lives in: <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
  - Wide charts (full-width): class="col-span-2"
  - Chart containers need explicit height: style="height:280px" or "height:320px"
  - Outer wrapper: class="p-6 min-h-screen bg-base-200"

CHART TYPE SELECTION GUIDE:
- Revenue/metric over time → area chart with gradient fill (type:'area', fill gradient)
- Category comparison → horizontal bar or stacked bar (type:'bar', horizontal:true)
- Part-of-whole breakdown → donut chart (type:'donut', hollow size 65%)
- Two metrics correlated → dual-axis line (yaxis array with opposite:true)
- Intensity over time/category → heatmap (type:'heatmap', colorScale)
- Funnel/stages → horizontal bar sorted descending with custom colors
- Sparklines in KPI cards → minimal area chart (height:60, no axes, no toolbar)

NUMBER FORMATTING (always use these helpers — never show raw integers):
Define this helper at the top of every component that displays money or large numbers:
  function fmtMoney(v) { return v >= 1e9 ? '$'+(v/1e9).toFixed(1)+'B' : v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }
  function fmtNum(v) { return v >= 1e9 ? (v/1e9).toFixed(1)+'B' : v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'k' : String(Math.round(v)); }
Use fmtMoney in yaxis.labels.formatter and tooltip.y.formatter for revenue charts.
Use fmtNum for count/volume axes. NEVER display raw numbers like 104658761 — always format.

CRITICAL — DATA FETCH (ALWAYS use this exact pattern for business data — NEVER invent endpoints):
async function fetchData() {
  var t = window.__DATA_MODE || 'sample';
  var res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mock: {profile: 'saas', scale: 'large', seed: 1}, data_mode: t})
  });
  return res.json();
}
var [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
// Choose profile to match the domain: 'ecommerce' | 'saas' | 'marketing' | 'finance' | 'sales'

DATA FIELD GUIDANCE FOR SAAS PROFILE:
- For MRR/ARR TREND CHARTS: use kpi_monthly (monthly granularity, reliable mrr/arr fields)
  Example: kpi_monthly.map(m => m.mrr) — these are populated, real monthly figures
- For DAILY metrics (signups, events, pageviews): use metrics (daily series)
  Note: metrics.mrr exists but may be 0 or sparse — prefer kpi_monthly for revenue trends
- For WATERFALL (New ARR / Expansion / Churn): use kpi_monthly.net_new_mrr * 12 for new ARR,
  derive expansion as mrr * 0.08, churn as mrr * churn_rate — kpi_monthly has all these fields
- For KPI CARDS: always read from kpi_monthly[last] for current period values

⚠️ SYNTHETIC DATA RULE: If the prompt asks for metrics that do NOT exist in any profile
(e.g., latency, p95/p99, error rates, SLOs, traces, CPU/memory, uptime %)
→ DO NOT fetch from the API. Instead, define ALL data as hardcoded synthetic JS arrays at the top of the component.
→ Example for observability: var services = [{name:'api-gateway',p95:42,p99:98,errors:0.8,rps:1240,uptime:99.97},{name:'auth-service',p95:18,p99:45,errors:0.2,rps:880,uptime:99.99},{name:'db-proxy',p95:6,p99:12,errors:0.05,rps:2100,uptime:100},{name:'worker',p95:120,p99:310,errors:1.4,rps:340,uptime:99.91}];
→ Use createSignal to hold this data (no createResource needed).
→ This avoids loading spinners and produces immediately interactive dashboards.

APEXCHARTS USAGE RULES — READ CAREFULLY:
1. ALWAYS use onMount (NOT createEffect) to initialize charts. createEffect fires before the ref is in the DOM.
2. ALWAYS call chart.destroy() in onCleanup to prevent memory leaks.
3. ALWAYS guard: if (!chartRef) return; before creating a chart instance.
4. For reactive data: inside onMount, use a createEffect that watches the data signal, then (re)creates the chart.
5. Chart options MUST include: chart.toolbar.show:false, chart.animations.enabled:false (for perf).
6. For gradient area charts use: fill:{ type:'gradient', gradient:{ shadeIntensity:1, opacityFrom:0.4, opacityTo:0.05, stops:[0,95,100] } }
7. For stacked bars: chart:{ stacked:true } and series as array of {name, data} objects.
8. Colors array: always pass colors:['#6366f1','#22d3ee','#f59e0b','#10b981','#ef4444'] unless chart has its own palette.
9. xaxis.labels.style and yaxis.labels.style: always set { colors:'#64748b', fontSize:'11px' }.
10. tooltip.theme: 'dark' always looks better.
11. For heatmaps: plotOptions.heatmap.colorScale.ranges defines color stops (low→mid→high).
12. Sparklines: chart:{ sparkline:{ enabled:true } } — omit all axes/toolbar/grid.
13. Always use fmtMoney/fmtNum in yaxis.labels.formatter — never show raw integers on axes.

WHEN TO GENERATE A RICH DASHBOARD (multi-chart layout):
Trigger rich dashboard mode when the prompt contains ANY of: dashboard, overview, analytics, metrics, intelligence, observability, health, report, summary, monitor, performance.
In rich dashboard mode:
- ALWAYS render 3–5 chart panels plus a KPI row (never just one chart)
- ALWAYS use the color palette and layout rules above
- Generate realistic mock data inline if the fetched data is not granular enough for the charts requested
- Label every chart clearly with a section header above it

AVAILABLE PRE-BUILT TEMPLATES (use for simple single-visualization requests):
1. StatCard - KPI cards with trend indicators
2. DataTable - Filterable/sortable tables
3. LineChart - Time series line charts
4. BarChart - Comparison bar charts
5. ListWithSearch - Searchable lists
6. DonutChart - Category breakdown donut/pie
7. HeatmapChart - Time-series intensity heatmap
8. MixedChart - Combined line + bar chart

Guidelines for component generation:
1. Use Solid.js primitives: createSignal, createEffect, createResource, For, Show, Switch, onMount, onCleanup
2. Style primarily with DaisyUI classes (e.g., btn, card, table, badge, input) combined with Tailwind utilities
3. Rich dashboards may be up to 300 lines — quality and completeness matter more than line count for dashboards
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

Example with ApexCharts — CORRECT onMount pattern (ALWAYS use onMount, never createEffect for chart init):

import { createResource, createEffect, onMount, onCleanup } from 'solid-js';
import ApexCharts from 'apexcharts';

async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: 'saas', scale: 'large', days: 90 }, data_mode: dataMode })
  });
  return response.json();
}

export default function RevenueChart() {
  const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  let chartRef;
  let chartInstance;

  onMount(function() {
    createEffect(function() {
      if (!apiData() || !apiData().metrics) return;
      const metrics = apiData().metrics;
      const options = {
        chart: { type: 'area', toolbar: { show: false }, animations: { enabled: false } },
        colors: ['#6366f1'],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 95, 100] } },
        stroke: { curve: 'smooth', width: 2 },
        series: [{ name: 'MRR', data: metrics.map(function(m) { return m.mrr || 0; }) }],
        xaxis: { categories: metrics.map(function(m) { return m.date; }), labels: { style: { colors: '#64748b', fontSize: '11px' } } },
        yaxis: { labels: { style: { colors: '#64748b', fontSize: '11px' }, formatter: function(v) { return '$' + (v/1000).toFixed(0) + 'k'; } } },
        tooltip: { theme: 'dark' },
        grid: { borderColor: '#1e293b' }
      };
      if (chartInstance) chartInstance.destroy();
      chartInstance = new ApexCharts(chartRef, options);
      chartInstance.render();
    });
  });

  onCleanup(function() {
    if (chartInstance) chartInstance.destroy();
  });

  return (
    <div class="p-6 bg-base-200 min-h-screen">
      <h2 class="text-2xl font-bold mb-4">Revenue Trend</h2>
      <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">Monthly Recurring Revenue</p>
        <div ref={chartRef} style="height:320px"></div>
      </div>
    </div>
  );
}

Example rich multi-chart dashboard (USE THIS PATTERN for any "dashboard" prompt):

import { createResource, createEffect, onMount, onCleanup, For, Show } from 'solid-js';
import ApexCharts from 'apexcharts';

async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: 'saas', scale: 'large', seed: 42, days: 180 }, data_mode: dataMode })
  });
  return res.json();
}

// Always define these helpers — never show raw integers
function fmtMoney(v) { return v >= 1e9 ? '$'+(v/1e9).toFixed(1)+'B' : v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }
function fmtNum(v) { return v >= 1e9 ? (v/1e9).toFixed(1)+'B' : v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'k' : String(Math.round(v)); }

function makeChart(ref, options, instances, key) {
  if (instances[key]) { instances[key].destroy(); }
  if (!ref) return;
  const c = new ApexCharts(ref, options);
  c.render();
  instances[key] = c;
}

export default function SaasDashboard() {
  const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  let revenueRef, churnRef, donutRef, heatRef;
  const charts = {};

  onMount(function() {
    createEffect(function() {
      const d = apiData();
      if (!d || !d.metrics) return;
      const metrics = d.metrics || [];
      const kpiMonthly = d.kpi_monthly || [];
      const COLORS = ['#6366f1','#22d3ee','#f59e0b','#10b981','#ef4444'];
      const labelStyle = { colors: '#64748b', fontSize: '11px' };
      const tooltipDark = { theme: 'dark' };
      const noToolbar = { show: false };
      const noAnim = { enabled: false };

      // Area chart — MRR trend
      makeChart(revenueRef, {
        chart: { type: 'area', toolbar: noToolbar, animations: noAnim },
        colors: [COLORS[0], COLORS[1]],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.02, stops: [0,95,100] } },
        stroke: { curve: 'smooth', width: 2 },
        series: [
          { name: 'MRR', data: kpiMonthly.map(function(m) { return Math.round((m.mrr || 0)); }) },
          { name: 'Net New MRR', data: kpiMonthly.map(function(m) { return Math.round((m.net_new_mrr || 0)); }) }
        ],
        xaxis: { categories: kpiMonthly.map(function(m) { return m.month || m.date || ''; }), tickAmount: 8, labels: { style: labelStyle } },
        yaxis: { labels: { style: labelStyle, formatter: function(v) { return fmtMoney(v); } } },
        tooltip: tooltipDark,
        grid: { borderColor: '#1e293b50' }
      }, charts, 'revenue');

      // Stacked bar — monthly breakdown
      makeChart(churnRef, {
        chart: { type: 'bar', stacked: true, toolbar: noToolbar, animations: noAnim },
        colors: [COLORS[0], COLORS[3], COLORS[4]],
        series: [
          { name: 'New ARR', data: kpiMonthly.slice(-12).map(function(m) { return Math.round((m.net_new_mrr || 0) * 12); }) },
          { name: 'Expansion', data: kpiMonthly.slice(-12).map(function(m) { return Math.round((m.mrr || 0) * 0.08); }) },
          { name: 'Churn', data: kpiMonthly.slice(-12).map(function(m) { return -Math.round((m.mrr || 0) * (m.churn_rate || 0.03)); }) }
        ],
        xaxis: { categories: kpiMonthly.slice(-12).map(function(m) { return m.month || m.date || ''; }), labels: { style: labelStyle } },
        yaxis: { labels: { style: labelStyle, formatter: function(v) { return fmtMoney(v); } } },
        tooltip: tooltipDark,
        plotOptions: { bar: { borderRadius: 3 } },
        grid: { borderColor: '#1e293b50' }
      }, charts, 'churn');

      // Donut — plan mix
      const plans = d.plans || [{ name:'Starter' },{ name:'Growth' },{ name:'Enterprise' }];
      makeChart(donutRef, {
        chart: { type: 'donut', toolbar: noToolbar, animations: noAnim },
        colors: COLORS,
        series: plans.map(function(p, i) { return 40 - i * 10 + Math.floor(Math.random() * 5); }),
        labels: plans.map(function(p) { return p.name || 'Plan ' + (i+1); }),
        plotOptions: { pie: { donut: { size: '65%', labels: { show: true, total: { show: true, label: 'Plans', color: '#64748b' } } } } },
        legend: { position: 'bottom', labels: { colors: '#64748b' } },
        tooltip: tooltipDark
      }, charts, 'donut');

      // Heatmap — daily activity by day-of-week
      const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
      const heatSeries = days.map(function(day) {
        return { name: day, data: Array.from({ length: 12 }, function(_, i) {
          return { x: 'W' + (i+1), y: Math.floor(Math.random() * 100) };
        })};
      });
      makeChart(heatRef, {
        chart: { type: 'heatmap', toolbar: noToolbar, animations: noAnim },
        colors: ['#6366f1'],
        series: heatSeries,
        plotOptions: { heatmap: { shadeIntensity: 0.8, radius: 2, colorScale: { ranges: [
          { from:0, to:30, color:'#1e1b4b', name:'Low' },
          { from:31, to:70, color:'#4338ca', name:'Mid' },
          { from:71, to:100, color:'#818cf8', name:'High' }
        ]}}},
        xaxis: { labels: { style: labelStyle } },
        yaxis: { labels: { style: labelStyle } },
        tooltip: tooltipDark,
        dataLabels: { enabled: false }
      }, charts, 'heat');
    });
  });

  onCleanup(function() {
    Object.keys(charts).forEach(function(k) { if (charts[k]) charts[k].destroy(); });
  });

  const kpis = function() {
    const d = apiData();
    if (!d || !d.kpi_monthly || !d.kpi_monthly.length) return [];
    const latest = d.kpi_monthly[d.kpi_monthly.length - 1] || {};
    const prev = d.kpi_monthly[d.kpi_monthly.length - 2] || {};
    return [
      { label: 'ARR', value: '$' + ((latest.arr || latest.mrr * 12 || 0) / 1000).toFixed(0) + 'k', delta: '+12%', up: true },
      { label: 'MRR', value: '$' + ((latest.mrr || 0) / 1000).toFixed(0) + 'k', delta: '+8%', up: true },
      { label: 'Churn Rate', value: ((latest.churn_rate || 0.03) * 100).toFixed(1) + '%', delta: '-0.3%', up: false },
      { label: 'Net Retention', value: ((latest.net_retention || 1.12) * 100).toFixed(0) + '%', delta: '+4pp', up: true }
    ];
  };

  return (
    <div class="p-6 bg-base-200 min-h-screen">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold">SaaS Dashboard</h1>
        <span class="badge badge-primary badge-outline">Live</span>
      </div>
      <Show when={!apiData.loading} fallback={<div class="flex items-center justify-center h-64"><span class="loading loading-spinner loading-lg text-primary"></span></div>}>
        <div class="grid grid-cols-4 gap-4 mb-6">
          <For each={kpis()}>
            {function(k) {
              return (
                <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
                  <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-1">{k.label}</p>
                  <p class="text-3xl font-bold tabular-nums">{k.value}</p>
                  <p class={k.up ? 'text-emerald-500 text-xs font-medium mt-1' : 'text-red-500 text-xs font-medium mt-1'}>{k.delta} vs last month</p>
                </div>
              );
            }}
          </For>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="card bg-base-100 shadow-sm border border-base-200 p-4 col-span-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">MRR Trend (60 days)</p>
            <div ref={revenueRef} style="height:280px"></div>
          </div>
          <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">ARR Waterfall (12mo)</p>
            <div ref={churnRef} style="height:260px"></div>
          </div>
          <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">Plan Mix</p>
            <div ref={donutRef} style="height:260px"></div>
          </div>
          <div class="card bg-base-100 shadow-sm border border-base-200 p-4 col-span-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">Activity Heatmap</p>
            <div ref={heatRef} style="height:200px"></div>
          </div>
        </div>
      </Show>
    </div>
  );
}

DATA BRIDGE (sample to real swap):
- window.__DATA_MODE is 'sample' by default. Parent can postMessage { type: 'data_swap', mode: 'real' } to switch.
- Include data_mode in fetch body. Use createResource(source, fetchData) with source = function() { return window.__DATA_MODE; } so refetch triggers on mode change.
- Real data: POST to /api/components/{id}/data/swap with { mode: 'real', data: {...} } before switching.

Respond only with valid JSON in the specified format. CRITICAL: Do NOT wrap code in markdown fences."""

        # ----------------------------------------------------------------
        # WIDGET PROMPT — single focused visualization, embeddable card
        # Target: 60-120 lines, one chart or one metric group, no full-page layout
        # ----------------------------------------------------------------
        self.widget_prompt = """You are an expert at generating beautiful embeddable widget micro-components.
You generate Spark native microapps: single-purpose Solid.js widgets designed to live in a grid alongside other widgets.
Visual quality bar: Grafana panel / Linear insight card / Stripe metric widget.

WIDGET DESIGN RULES:
- One chart OR one metric group per widget — never multiple chart panels
- Card wrapper: <div class="card bg-base-100 shadow-sm border border-base-200 p-4 h-full">
- Always include a compact header: <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">TITLE</p>
- Chart height: 200-240px (not full page — designed to be embedded in a grid)
- ⚠️ FORBIDDEN: NO outer page wrapper. Do NOT add bg-base-200, min-h-screen, p-6, or any wrapping div outside the card. The widget IS the card — start your JSX with <div class="card ...">
- Keep component under 120 lines
- Colors: #6366f1 primary, #22d3ee secondary, #f59e0b amber, #10b981 emerald, #ef4444 red

CRITICAL — DATA FETCH (ALWAYS use this exact pattern, never invent endpoints):
async function fetchData() {
  var res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mock: {profile: 'ecommerce', scale: 'medium', seed: 1}, data_mode: window.__DATA_MODE || 'sample'})
  });
  return res.json();
}
// Then: const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
// Available profiles: 'ecommerce' | 'saas' | 'marketing' | 'finance' | 'sales'
// ecommerce: data.products[]{id,name,category,price,stock}, data.sales[]{revenue,product,date}, data.summary{total_revenue,total_orders}
// saas:      data.kpi_monthly[]{month,mrr,arr,churn_rate,net_retention}  ← USE THIS for MRR/ARR trends
//            data.metrics[] is DAILY raw data — do NOT use for trend charts
//            data.plans[]{name,count,mrr}, data.accounts[]{name,mrr,health}
// finance:   data.pnl_monthly[]{month,revenue,gross_profit,ebitda}, data.transactions[]
// sales:     data.opportunities[]{name,amount,stage}, data.reps[]{name,quota,attainment}
// ⚠️ For MRR/ARR/churn trends: ALWAYS use data.kpi_monthly[], NEVER data.metrics[]
// Always guard: if (!apiData() || !apiData().kpi_monthly) return null;

NUMBER FORMATTING (define at top of component, always use — never show raw integers):
function fmtMoney(v) { return v >= 1e9 ? '$'+(v/1e9).toFixed(1)+'B' : v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }
function fmtNum(v) { return v >= 1e9 ? (v/1e9).toFixed(1)+'B' : v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'k' : String(Math.round(v)); }

APEXCHARTS: import ApexCharts from 'apexcharts'. Always onMount + inner createEffect. toolbar.show:false, animations.enabled:false. onCleanup to destroy.
SOLID.JS: createResource, onMount, onCleanup, For, Show from 'solid-js'. ES2015 only. No optional chaining (?.) or nullish coalescing (??).
No window/document/localStorage — only createResource for async data.

Example widget (MRR trend card):
import { createResource, onMount, onCleanup, createEffect, Show } from 'solid-js';
import ApexCharts from 'apexcharts';
function fmtMoney(v) { return v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }
async function fetchData() {
  var res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mock: {profile: 'saas', scale: 'medium', seed: 1}, data_mode: window.__DATA_MODE || 'sample'})
  });
  return res.json();
}
export default function MRRWidget() {
  var [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  var chartRef, chartInstance;
  onMount(function() {
    createEffect(function() {
      var d = apiData();
      if (!d || !d.kpi_monthly || !chartRef) return;
      var months = d.kpi_monthly;
      if (chartInstance) chartInstance.destroy();
      chartInstance = new ApexCharts(chartRef, {
        chart: { type: 'area', height: 220, toolbar: { show: false }, animations: { enabled: false } },
        colors: ['#6366f1'],
        fill: { type: 'gradient', gradient: { opacityFrom: 0.35, opacityTo: 0.02 } },
        stroke: { curve: 'smooth', width: 2 },
        dataLabels: { enabled: false },
        series: [{ name: 'MRR', data: months.map(function(m) { return m.mrr || 0; }) }],
        xaxis: { categories: months.map(function(m) { return m.month || ''; }), labels: { style: { colors: '#64748b', fontSize: '11px' } } },
        yaxis: { labels: { style: { colors: '#64748b', fontSize: '11px' }, formatter: function(v) { return fmtMoney(v); } } },
        tooltip: { theme: 'dark', y: { formatter: function(v) { return fmtMoney(v); } } },
        grid: { borderColor: '#1e293b50' }
      });
      chartInstance.render();
    });
  });
  onCleanup(function() { if (chartInstance) chartInstance.destroy(); });
  return (
    <div class="card bg-base-100 shadow-sm border border-base-200 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">MRR Trend</p>
      <Show when={!apiData.loading} fallback={<div class="flex items-center justify-center h-48"><span class="loading loading-spinner text-primary"></span></div>}>
        <div ref={chartRef} style="height:220px"></div>
      </Show>
    </div>
  );
}

Response format (JSON, no markdown fences):
{"type": "component", "content": "<complete Solid.js widget code>", "reasoning": "<brief note>"}"""

        # ----------------------------------------------------------------
        # QUICK PROMPT — ephemeral inline chat render, appears in thread
        # Target: 30-70 lines, instant readable answer, table or mini-chart
        # ----------------------------------------------------------------
        self.quick_prompt = """You are an expert at generating fast, readable inline data components for chat interfaces.
You generate Spark native microapps: lightweight Solid.js components that render instantly inside a chat thread.
Think: ChatGPT data analyst answer, Perplexity inline table — not a dashboard.

QUICK RENDER RULES:
- Prefer a clean table or stat over a chart when data is tabular
- Minimal styling — render on the chat background: <div class="p-3">
- Max 300px total height. Readable at a glance without interaction.
- Use DaisyUI table: <table class="table table-sm table-zebra w-full">
- For a single KPI: <div class="stats shadow"><div class="stat"><div class="stat-title">X</div><div class="stat-value">Y</div></div></div>
- For a mini bar chart: ApexCharts height:160, sparkline enabled, no axes

CRITICAL — DATA FETCH (ALWAYS use this exact pattern — NEVER invent endpoints):
async function fetchData() {
  var res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mock: {profile: 'ecommerce', scale: 'small', seed: 1}, data_mode: window.__DATA_MODE || 'sample'})
  });
  return res.json();
}
const [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
// Profile field reference:
// ecommerce: data.products[]{id,name,category,price,stock,rating}, data.sales[]{revenue,product,date,region}, data.summary{total_revenue,total_orders}
// saas: data.kpi_monthly[]{mrr,arr,churn_rate,net_retention}, data.plans[]{name}
// finance: data.pnl_monthly[]{revenue,gross_profit,ebitda}, data.transactions[]
// sales: data.opportunities[]{amount,stage}, data.reps[]{name,quota}
// ALWAYS guard: if (!apiData() || !apiData().products) return null;

NUMBER FORMATTING (define in component, always use — never raw integers):
function fmtMoney(v) { return v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }

SOLID.JS rules: createResource, For, Show, onMount, onCleanup from 'solid-js'. ES2015 only. No ?. or ??. No fetch directly — use createResource.

Example quick component (top products table):
import { createResource, For, Show } from 'solid-js';
function fmtMoney(v) { return v >= 1e6 ? '$'+(v/1e6).toFixed(1)+'M' : v >= 1e3 ? '$'+(v/1e3).toFixed(0)+'k' : '$'+Math.round(v); }
async function fetchData() {
  var res = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mock: {profile: 'ecommerce', scale: 'small', seed: 1}, data_mode: window.__DATA_MODE || 'sample'})
  });
  return res.json();
}
export default function TopProducts() {
  var [apiData] = createResource(function() { return window.__DATA_MODE || 'sample'; }, fetchData);
  var top = function() {
    if (!apiData() || !apiData().products) return [];
    return apiData().products.slice().sort(function(a, b) { return (b.price * (b.stock || 1)) - (a.price * (a.stock || 1)); }).slice(0, 5);
  };
  return (
    <div class="p-3">
      <p class="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-2">Top 5 Products by Revenue</p>
      <Show when={!apiData.loading} fallback={<span class="loading loading-spinner loading-sm"></span>}>
        <table class="table table-sm table-zebra w-full">
          <thead><tr><th>Product</th><th>Category</th><th>Price</th></tr></thead>
          <tbody>
            <For each={top()}>{function(p) {
              return <tr><td>{p.name}</td><td>{p.category}</td><td>{fmtMoney(p.price)}</td></tr>;
            }}</For>
          </tbody>
        </table>
      </Show>
    </div>
  );
}

Response format (JSON, no markdown fences):
{"type": "component" or "text", "content": "<Solid.js code or plain answer>", "reasoning": "<brief note>"}"""

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

    # Keywords that force a specific generation mode regardless of explicit param
    _DASHBOARD_KEYWORDS = {"dashboard", "overview", "analytics", "intelligence", "observability",
                           "health", "report", "summary", "monitor", "performance", "metrics"}
    _QUICK_KEYWORDS = {"quick", "show me", "what is", "how many", "give me", "tell me",
                       "what's", "whats", "current", "today", "right now", "fast"}

    def _detect_mode(self, user_message: str) -> str:
        """Auto-detect generation mode from prompt if not explicitly provided."""
        msg = user_message.lower()
        words = set(msg.replace("?", "").replace(",", "").split())
        # Explicit dashboard intent
        if words & self._DASHBOARD_KEYWORDS:
            return "dashboard"
        # Short/quick queries
        if len(user_message.split()) <= 8 or (words & self._QUICK_KEYWORDS):
            return "quick"
        # Default to widget for everything else (single focused viz)
        return "widget"

    def _get_system_prompt_for_mode(self, mode: str) -> str:
        if mode == "dashboard":
            return self.system_prompt
        elif mode == "widget":
            return self.widget_prompt
        elif mode == "quick":
            return self.quick_prompt
        return self.system_prompt

    async def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        llm_config: Optional[LLMConfig] = None,
        mode: Optional[str] = None,
    ) -> ChatResponse:
        if conversation_history is None:
            conversation_history = []

        gateway = LLMGateway(llm_config) if llm_config else self.gateway

        # Resolve generation mode
        resolved_mode = mode if mode in ("dashboard", "widget", "quick") else self._detect_mode(user_message)
        logger.info(f"Generation mode: {resolved_mode} (requested={mode})")

        # Check prompt cache first
        cached_response = await self.prompt_cache.get_cached_response(user_message, resolved_mode)
        if cached_response:
            logger.info("Using cached LLM response")
            return cached_response

        self._refresh_style_reference()
        style_snippet = self._get_style_reference_snippet()
        system_prompt = self._get_system_prompt_for_mode(resolved_mode)
        if style_snippet and resolved_mode == "dashboard":
            # Only append heavy DaisyUI reference for full dashboards
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

            await self.prompt_cache.cache_response(user_message, resolved_mode, response)
            # Attach resolved mode so callers can use it for iframe sizing etc.
            response.meta = {"mode": resolved_mode}
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
