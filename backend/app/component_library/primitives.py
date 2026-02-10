"""Reusable SolidJS hooks, utilities, and helper functions."""

from typing import Dict

# Standard data fetching pattern
DATA_FETCH_PRIMITIVE = """// Standard data fetching with createResource
async function fetchData(profile = 'ecommerce', scale = 'medium', days = 180) {
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mock: { profile, scale, days } })
  });
  return response.json();
}"""

# Filtering logic
FILTER_PRIMITIVE = """// Client-side filtering
const useFilter = (items, filterText, fields) => {
  const filtered = () => {
    if (!items() || !filterText()) return items() || [];
    const f = filterText().toLowerCase();
    return items().filter(function(item) {
      return fields.some(function(field) {
        const val = item[field];
        return val && String(val).toLowerCase().includes(f);
      });
    });
  };
  return filtered;
};"""

# Sorting logic
SORT_PRIMITIVE = """// Client-side sorting
const useSort = (items, sortField, sortDirection) => {
  const sorted = () => {
    if (!items()) return [];
    const field = sortField();
    const dir = sortDirection();
    return [...items()].sort(function(a, b) {
      if (a[field] < b[field]) return dir === 'asc' ? -1 : 1;
      if (a[field] > b[field]) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  };
  return sorted;
};"""

# Currency formatting
FORMAT_CURRENCY_PRIMITIVE = """// Format currency values
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value;
  if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
  if (value >= 1000) return '$' + (value / 1000).toFixed(1) + 'K';
  return '$' + value.toFixed(2);
};"""

# Date formatting
FORMAT_DATE_PRIMITIVE = """// Format date strings
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
};"""

# Number formatting
FORMAT_NUMBER_PRIMITIVE = """// Format large numbers
const formatNumber = (value) => {
  if (typeof value !== 'number') return value;
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
  return value.toFixed(0);
};"""

# Percentage formatting
FORMAT_PERCENT_PRIMITIVE = """// Format percentage values
const formatPercent = (value) => {
  if (typeof value !== 'number') return value;
  return (value * 100).toFixed(1) + '%';
};"""

# ApexCharts line chart config
APEX_LINE_CONFIG = """// ApexCharts line chart configuration
const apexLineConfig = (categories, data, name) => ({
  chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false } },
  stroke: { curve: 'smooth', width: 2 },
  series: [{ name: name || 'Value', data: data }],
  xaxis: { categories: categories },
  yaxis: { min: 0 },
  tooltip: { enabled: true },
  colors: ['#22c55e']
});"""

# ApexCharts bar chart config
APEX_BAR_CONFIG = """// ApexCharts bar chart configuration
const apexBarConfig = (categories, data, name) => ({
  chart: { type: 'bar', toolbar: { show: false } },
  plotOptions: {
    bar: {
      borderRadius: 4,
      columnWidth: '60%',
      dataLabels: { position: 'top' }
    }
  },
  series: [{ name: name || 'Value', data: data }],
  xaxis: { categories: categories },
  yaxis: { min: 0 },
  tooltip: { enabled: true },
  colors: ['#3b82f6']
});"""

# ApexCharts area chart config
APEX_AREA_CONFIG = """// ApexCharts area chart configuration
const apexAreaConfig = (categories, data, name) => ({
  chart: { type: 'area', toolbar: { show: false } },
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { opacityFrom: 0.6, opacityTo: 0.1 } },
  series: [{ name: name || 'Value', data: data }],
  xaxis: { categories: categories },
  yaxis: { min: 0 },
  tooltip: { enabled: true },
  colors: ['#8b5cf6']
});"""

# ApexCharts donut chart config
APEX_DONUT_CONFIG = """// ApexCharts donut chart configuration
const apexDonutConfig = (labels, data) => ({
  chart: { type: 'donut' },
  labels: labels,
  series: data,
  legend: { position: 'right' },
  colors: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'],
  plotOptions: {
    pie: {
      donut: { size: '60%' }
    }
  }
});"""

# ApexCharts sparkline config
APEX_SPARKLINE_CONFIG = """// ApexCharts sparkline configuration (minimal inline charts)
const apexSparklineConfig = (data, color) => ({
  chart: { type: 'area', sparkline: { enabled: true } },
  stroke: { curve: 'smooth' },
  fill: { opacity: 0.3 },
  series: [{ data: data }],
  colors: [color || '#22c55e']
});"""

# ApexCharts mixed chart config (line + bar)
APEX_MIXED_CONFIG = """// ApexCharts mixed chart configuration (line + bar)
const apexMixedConfig = (categories, lineData, barData, lineName, barName) => ({
  chart: { type: 'line', toolbar: { show: false } },
  stroke: { width: [2, 0] },
  plotOptions: {
    bar: { columnWidth: '50%' }
  },
  series: [
    { name: lineName || 'Line', type: 'line', data: lineData },
    { name: barName || 'Bar', type: 'column', data: barData }
  ],
  xaxis: { categories: categories },
  yaxis: [{ min: 0 }, { opposite: true, min: 0 }],
  tooltip: { shared: true }
});"""

# Legacy Chart.js aliases (for backward compatibility - now map to ApexCharts)
CHART_LINE_CONFIG = APEX_LINE_CONFIG
CHART_BAR_CONFIG = APEX_BAR_CONFIG
CHART_PIE_CONFIG = APEX_DONUT_CONFIG

# Data Bridge Primitives

DATA_CONTEXT_SETUP = """// Data bridge context setup - use with createContext
import { createContext, useContext } from 'solid-js';

const DataContext = createContext({ data: null, mode: 'sample' });

export function DataProvider(props) {
  return (
    <DataContext.Provider value={{ data: props.data, mode: props.mode || 'sample' }}>
      {props.children}
    </DataContext.Provider>
  );
}

export function useDashboardData() {
  const ctx = useContext(DataContext);
  return ctx;
}"""

DATA_VALIDATOR = """// Runtime schema validation - valid approximate shape
function validateDataShape(data, expectedKeys) {
  if (!data || typeof data !== 'object') return { valid: false, missing: expectedKeys };
  const missing = expectedKeys.filter(function(k) { return !(k in data); });
  return { valid: missing.length === 0, missing: missing };
}"""

DATA_TRANSFORMER = """// Format/normalize data for chart consumption
function transformToChartFormat(items, xField, yField) {
  if (!Array.isArray(items)) return [];
  return items.map(function(item) {
    return { x: item[xField], y: item[yField] };
  });
}"""

USE_DATA_BRIDGE = """// Hook for consuming data bridge context (sample/real swap)
function useDataBridge() {
  const ctx = useContext(DataContext);
  const data = () => ctx?.data || null;
  const mode = () => ctx?.mode || 'sample';
  const isReal = () => mode() === 'real';
  return { data, mode, isReal };
}"""

# Pagination helper
PAGINATION_PRIMITIVE = """// Pagination helper
const usePagination = (items, pageSize = 10) => {
  const [page, setPage] = createSignal(1);
  
  const totalPages = () => Math.ceil((items()?.length || 0) / pageSize);
  
  const paginatedItems = () => {
    if (!items()) return [];
    const start = (page() - 1) * pageSize;
    return items().slice(start, start + pageSize);
  };
  
  const nextPage = () => {
    if (page() < totalPages()) setPage(page() + 1);
  };
  
  const prevPage = () => {
    if (page() > 1) setPage(page() - 1);
  };
  
  return { paginatedItems, page, totalPages, nextPage, prevPage, setPage };
};"""

# Debounce helper
DEBOUNCE_PRIMITIVE = """// Debounce helper for search inputs
const createDebounced = (signal, delay = 300) => {
  const [debounced, setDebounced] = createSignal(signal());
  let timeout;
  
  createEffect(() => {
    const value = signal();
    clearTimeout(timeout);
    timeout = setTimeout(() => setDebounced(value), delay);
  });
  
  return debounced;
};"""

# Loading skeleton
LOADING_SKELETON = """// Loading skeleton component
const LoadingSkeleton = () => (
  <div class="animate-pulse space-y-4">
    <div class="h-4 bg-base-300 rounded w-3/4"></div>
    <div class="h-4 bg-base-300 rounded w-1/2"></div>
    <div class="h-4 bg-base-300 rounded w-5/6"></div>
  </div>
);"""

# Error display
ERROR_DISPLAY = """// Error display component
const ErrorDisplay = (props) => (
  <div class="alert alert-error">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <span>{props.message || 'An error occurred'}</span>
  </div>
);"""


# Collection of all primitives
SOLIDJS_PRIMITIVES: Dict[str, str] = {
    "data_fetch": DATA_FETCH_PRIMITIVE,
    "filter": FILTER_PRIMITIVE,
    "sort": SORT_PRIMITIVE,
    "format_currency": FORMAT_CURRENCY_PRIMITIVE,
    "format_date": FORMAT_DATE_PRIMITIVE,
    "format_number": FORMAT_NUMBER_PRIMITIVE,
    "format_percent": FORMAT_PERCENT_PRIMITIVE,
    "chart_line_config": CHART_LINE_CONFIG,
    "chart_bar_config": CHART_BAR_CONFIG,
    "chart_pie_config": CHART_PIE_CONFIG,
    "apex_line_config": APEX_LINE_CONFIG,
    "apex_bar_config": APEX_BAR_CONFIG,
    "apex_area_config": APEX_AREA_CONFIG,
    "apex_donut_config": APEX_DONUT_CONFIG,
    "apex_sparkline_config": APEX_SPARKLINE_CONFIG,
    "apex_mixed_config": APEX_MIXED_CONFIG,
    "data_context_setup": DATA_CONTEXT_SETUP,
    "data_validator": DATA_VALIDATOR,
    "data_transformer": DATA_TRANSFORMER,
    "use_data_bridge": USE_DATA_BRIDGE,
    "pagination": PAGINATION_PRIMITIVE,
    "debounce": DEBOUNCE_PRIMITIVE,
    "loading_skeleton": LOADING_SKELETON,
    "error_display": ERROR_DISPLAY,
}


def get_primitive(name: str) -> str:
    """Get a primitive by name."""
    return SOLIDJS_PRIMITIVES.get(name, "")


def get_common_imports() -> str:
    """Get common SolidJS imports used across components."""
    return "import { createSignal, createResource, createEffect, For, Show, onMount, onCleanup } from 'solid-js';"

