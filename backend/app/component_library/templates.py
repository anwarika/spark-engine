"""Pre-built SolidJS component templates for rapid generation."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ComponentTemplate:
    """A pre-built component template."""
    name: str
    category: str  # 'chart', 'table', 'card', 'dashboard', 'list'
    description: str
    code: str
    tags: List[str]
    data_requirements: List[str]  # What data fields are expected


# StatCard Template - KPI cards with trend indicators
STAT_CARD_TEMPLATE = ComponentTemplate(
    name="StatCard",
    category="card",
    description="Single KPI metric card with trend indicator",
    tags=["kpi", "metric", "card", "stat"],
    data_requirements=["title", "value", "trend"],
    code="""import { createSignal, createResource } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'medium' } })
  });
  return response.json();
}

export default function StatCard() {
  const [data] = createResource(fetchData);
  
  const formatValue = (val) => {
    if (typeof val === 'number') {
      if (val > 1000000) return '$' + (val / 1000000).toFixed(1) + 'M';
      if (val > 1000) return '$' + (val / 1000).toFixed(1) + 'K';
      return '$' + val.toFixed(0);
    }
    return val;
  };
  
  return (
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card bg-base-100 shadow-lg">
          <div class="card-body">
            <h3 class="text-sm font-medium text-base-content/70">{{TITLE_1}}</h3>
            <div class="text-3xl font-bold">{data.loading ? '...' : formatValue(data()?.summary?.{{VALUE_1}})}</div>
            <div class="text-sm text-success">+{{TREND_1}}%</div>
          </div>
        </div>
        <div class="card bg-base-100 shadow-lg">
          <div class="card-body">
            <h3 class="text-sm font-medium text-base-content/70">{{TITLE_2}}</h3>
            <div class="text-3xl font-bold">{data.loading ? '...' : formatValue(data()?.summary?.{{VALUE_2}})}</div>
            <div class="text-sm text-success">+{{TREND_2}}%</div>
          </div>
        </div>
        <div class="card bg-base-100 shadow-lg">
          <div class="card-body">
            <h3 class="text-sm font-medium text-base-content/70">{{TITLE_3}}</h3>
            <div class="text-3xl font-bold">{data.loading ? '...' : (data()?.summary?.{{VALUE_3}} || 0).toFixed(2)}</div>
          </div>
        </div>
        <div class="card bg-base-100 shadow-lg">
          <div class="card-body">
            <h3 class="text-sm font-medium text-base-content/70">{{TITLE_4}}</h3>
            <div class="text-3xl font-bold">{data.loading ? '...' : data()?.summary?.{{VALUE_4}}}</div>
          </div>
        </div>
      </div>
    </div>
  );
}"""
)


# DataTable Template - Filterable, sortable table
DATA_TABLE_TEMPLATE = ComponentTemplate(
    name="DataTable",
    category="table",
    description="Filterable and sortable data table with search",
    tags=["table", "data", "filter", "sort", "search"],
    data_requirements=["data_array", "columns"],
    code="""import { createSignal, createResource, For, Show } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'medium' } })
  });
  return response.json();
}

export default function DataTable() {
  const [apiData] = createResource(fetchData);
  const [filter, setFilter] = createSignal('');
  const [sortField, setSortField] = createSignal('{{DEFAULT_SORT}}');
  const [sortDir, setSortDir] = createSignal('asc');
  
  const filteredData = () => {
    if (!apiData() || !apiData().{{DATA_ARRAY}}) return [];
    const f = filter().toLowerCase();
    let items = apiData().{{DATA_ARRAY}};
    
    if (f) {
      items = items.filter(function(item) {
        return JSON.stringify(item).toLowerCase().includes(f);
      });
    }
    
    const field = sortField();
    const dir = sortDir();
    return items.sort(function(a, b) {
      if (a[field] < b[field]) return dir === 'asc' ? -1 : 1;
      if (a[field] > b[field]) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  };
  
  const toggleSort = (field) => {
    if (sortField() === field) {
      setSortDir(sortDir() === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };
  
  return (
    <div class="p-6">
      <div class="mb-4 flex justify-between items-center">
        <h2 class="text-2xl font-bold">{{TABLE_TITLE}}</h2>
        <input
          type="text"
          class="input input-bordered w-64"
          placeholder="Search..."
          value={filter()}
          onInput={(e) => setFilter(e.target.value)}
        />
      </div>
      <Show when={!apiData.loading} fallback={<div class="loading loading-spinner loading-lg"></div>}>
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                {{TABLE_HEADERS}}
              </tr>
            </thead>
            <tbody>
              <For each={filteredData()}>
                {function(item) {
                  return (
                    <tr>
                      {{TABLE_CELLS}}
                    </tr>
                  );
                }}
              </For>
            </tbody>
          </table>
        </div>
        <div class="mt-4 text-sm text-base-content/70">
          Showing {filteredData().length} items
        </div>
      </Show>
    </div>
  );
}"""
)


# LineChart Template - Time series visualization
LINE_CHART_TEMPLATE = ComponentTemplate(
    name="LineChart",
    category="chart",
    description="Time series line chart for trends",
    tags=["chart", "line", "timeseries", "trend"],
    data_requirements=["date_field", "value_field"],
    code="""import { createSignal, createResource, onMount } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'medium', days: 90 } })
  });
  return response.json();
}

export default function LineChart() {
  const [apiData] = createResource(fetchData);
  let chartRef;
  
  onMount(function() {
    // Chart.js is available globally as window.Chart
    const Chart = window.Chart;
    if (!Chart) {
      console.error('Chart.js not available');
      return;
    }
    
    const renderChart = () => {
      if (!apiData() || !apiData().metrics) return;
      
      const ctx = chartRef.getContext('2d');
      const metrics = apiData().metrics;
      
      new Chart(ctx, {
          type: 'line',
          data: {
            labels: metrics.map(function(m) { return m.{{DATE_FIELD}}; }),
            datasets: [{
              label: '{{METRIC_LABEL}}',
              data: metrics.map(function(m) { return m.{{VALUE_FIELD}}; }),
              borderColor: 'rgb(75, 192, 192)',
              tension: 0.1,
              fill: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: true,
                position: 'top'
              }
            },
            scales: {
              y: {
                beginAtZero: true
              }
            }
          }
        });
      };
      
      if (apiData()) renderChart();
    });
  });
  
  return (
    <div class="p-6">
      <h2 class="text-2xl font-bold mb-4">{{CHART_TITLE}}</h2>
      <div style="height: 400px;">
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
}"""
)


# BarChart Template - Comparison visualization
BAR_CHART_TEMPLATE = ComponentTemplate(
    name="BarChart",
    category="chart",
    description="Bar chart for comparisons",
    tags=["chart", "bar", "comparison"],
    data_requirements=["category_field", "value_field"],
    code="""import { createSignal, createResource, onMount } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'medium' } })
  });
  return response.json();
}

export default function BarChart() {
  const [apiData] = createResource(fetchData);
  let chartRef;
  
  onMount(function() {
    // Chart.js is available globally as window.Chart
    const Chart = window.Chart;
    if (!Chart) {
      console.error('Chart.js not available');
      return;
    }
    
    const renderChart = () => {
      if (!apiData() || !apiData().{{DATA_ARRAY}}) return;
      
      const ctx = chartRef.getContext('2d');
      const items = apiData().{{DATA_ARRAY}}.slice(0, 10);
      
      new Chart(ctx, {
          type: 'bar',
          data: {
            labels: items.map(function(item) { return item.{{CATEGORY_FIELD}}; }),
            datasets: [{
              label: '{{VALUE_LABEL}}',
              data: items.map(function(item) { return item.{{VALUE_FIELD}}; }),
              backgroundColor: 'rgba(54, 162, 235, 0.5)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              }
            },
            scales: {
              y: {
                beginAtZero: true
              }
            }
          }
        });
      };
      
      if (apiData()) renderChart();
    });
  });
  
  return (
    <div class="p-6">
      <h2 class="text-2xl font-bold mb-4">{{CHART_TITLE}}</h2>
      <div style="height: 400px;">
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
}"""
)


# ListWithSearch Template - Searchable list with categories
LIST_WITH_SEARCH_TEMPLATE = ComponentTemplate(
    name="ListWithSearch",
    category="list",
    description="Searchable list with categories and badges",
    tags=["list", "search", "filter", "category"],
    data_requirements=["items_array", "name_field", "category_field"],
    code="""import { createSignal, createResource, For, Show } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'medium' } })
  });
  return response.json();
}

export default function ListWithSearch() {
  const [apiData] = createResource(fetchData);
  const [filter, setFilter] = createSignal('');
  const [categoryFilter, setCategoryFilter] = createSignal('all');
  
  const categories = () => {
    if (!apiData() || !apiData().{{ITEMS_ARRAY}}) return [];
    const cats = new Set();
    apiData().{{ITEMS_ARRAY}}.forEach(function(item) {
      cats.add(item.{{CATEGORY_FIELD}});
    });
    return Array.from(cats);
  };
  
  const filteredItems = () => {
    if (!apiData() || !apiData().{{ITEMS_ARRAY}}) return [];
    const f = filter().toLowerCase();
    const cat = categoryFilter();
    
    return apiData().{{ITEMS_ARRAY}}.filter(function(item) {
      const matchesSearch = !f || item.{{NAME_FIELD}}.toLowerCase().includes(f);
      const matchesCategory = cat === 'all' || item.{{CATEGORY_FIELD}} === cat;
      return matchesSearch && matchesCategory;
    });
  };
  
  return (
    <div class="p-6">
      <h2 class="text-2xl font-bold mb-4">{{LIST_TITLE}}</h2>
      
      <div class="mb-4 flex gap-4">
        <input
          type="text"
          class="input input-bordered flex-1"
          placeholder="Search..."
          value={filter()}
          onInput={(e) => setFilter(e.target.value)}
        />
        <select
          class="select select-bordered w-48"
          value={categoryFilter()}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="all">All Categories</option>
          <For each={categories()}>
            {function(cat) {
              return <option value={cat}>{cat}</option>;
            }}
          </For>
        </select>
      </div>
      
      <Show when={!apiData.loading} fallback={<div class="loading loading-spinner loading-lg"></div>}>
        <div class="grid gap-4">
          <For each={filteredItems()}>
            {function(item) {
              return (
                <div class="card bg-base-100 shadow">
                  <div class="card-body p-4">
                    <div class="flex justify-between items-start">
                      <div>
                        <h3 class="font-semibold text-lg">{item.{{NAME_FIELD}}}</h3>
                        {{ITEM_DETAILS}}
                      </div>
                      <span class="badge badge-secondary">{item.{{CATEGORY_FIELD}}}</span>
                    </div>
                  </div>
                </div>
              );
            }}
          </For>
        </div>
        <div class="mt-4 text-sm text-base-content/70">
          Showing {filteredItems().length} of {apiData().{{ITEMS_ARRAY}}.length} items
        </div>
      </Show>
    </div>
  );
}"""
)


# MetricsDashboard Template - Multi-stat overview
METRICS_DASHBOARD_TEMPLATE = ComponentTemplate(
    name="MetricsDashboard",
    category="dashboard",
    description="Multi-metric dashboard with cards and chart",
    tags=["dashboard", "metrics", "kpi", "overview"],
    data_requirements=["metrics", "summary"],
    code="""import { createSignal, createResource, For, Show, onMount } from 'solid-js';

async function fetchData() {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile: '{{PROFILE}}', scale: 'large', days: 90 } })
  });
  return response.json();
}

export default function MetricsDashboard() {
  const [apiData] = createResource(fetchData);
  let chartRef;
  
  const formatCurrency = (val) => {
    if (val > 1000000) return '$' + (val / 1000000).toFixed(1) + 'M';
    if (val > 1000) return '$' + (val / 1000).toFixed(1) + 'K';
    return '$' + val.toFixed(0);
  };
  
  onMount(function() {
    // Chart.js is available globally as window.Chart
    const Chart = window.Chart;
    if (!Chart) {
      console.error('Chart.js not available');
      return;
    }
    
    const renderChart = () => {
      if (!apiData() || !apiData().metrics) return;
      
      const ctx = chartRef.getContext('2d');
      const metrics = apiData().metrics.slice(-30);
      
      new Chart(ctx, {
          type: 'line',
          data: {
            labels: metrics.map(function(m) { return m.date; }),
            datasets: [{
              label: '{{CHART_METRIC}}',
              data: metrics.map(function(m) { return m.{{CHART_VALUE}}; }),
              borderColor: 'rgb(75, 192, 192)',
              tension: 0.3,
              fill: true,
              backgroundColor: 'rgba(75, 192, 192, 0.1)'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false }
            },
            scales: {
              y: { beginAtZero: true }
            }
          }
        });
      };
      
      if (apiData()) renderChart();
    });
  });
  
  return (
    <div class="p-6">
      <h1 class="text-3xl font-bold mb-6">{{DASHBOARD_TITLE}}</h1>
      
      <Show when={!apiData.loading} fallback={<div class="loading loading-spinner loading-lg"></div>}>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {{STAT_CARDS}}
        </div>
        
        <div class="card bg-base-100 shadow-lg mb-6">
          <div class="card-body">
            <h2 class="card-title">Trend Over Time</h2>
            <div style="height: 300px;">
              <canvas ref={chartRef}></canvas>
            </div>
          </div>
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <h2 class="card-title">Recent Activity</h2>
              {{RECENT_ITEMS}}
            </div>
          </div>
          <div class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <h2 class="card-title">Summary</h2>
              {{SUMMARY_ITEMS}}
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
}"""
)


# Collection of all templates
COMPONENT_TEMPLATES: Dict[str, ComponentTemplate] = {
    "StatCard": STAT_CARD_TEMPLATE,
    "DataTable": DATA_TABLE_TEMPLATE,
    "LineChart": LINE_CHART_TEMPLATE,
    "BarChart": BAR_CHART_TEMPLATE,
    "ListWithSearch": LIST_WITH_SEARCH_TEMPLATE,
    "MetricsDashboard": METRICS_DASHBOARD_TEMPLATE,
}


def get_template_by_name(name: str) -> Optional[ComponentTemplate]:
    """Get a template by name."""
    return COMPONENT_TEMPLATES.get(name)


def list_templates(category: Optional[str] = None, tags: Optional[List[str]] = None) -> List[ComponentTemplate]:
    """List templates, optionally filtered by category or tags."""
    templates = list(COMPONENT_TEMPLATES.values())
    
    if category:
        templates = [t for t in templates if t.category == category]
    
    if tags:
        templates = [t for t in templates if any(tag in t.tags for tag in tags)]
    
    return templates

