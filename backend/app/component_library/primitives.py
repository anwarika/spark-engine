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

# Chart.js line chart config
CHART_LINE_CONFIG = """// Chart.js line chart configuration
const lineChartConfig = (labels, data, label) => ({
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: label,
      data: data,
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.1)',
      tension: 0.3,
      fill: true
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
});"""

# Chart.js bar chart config
CHART_BAR_CONFIG = """// Chart.js bar chart configuration
const barChartConfig = (labels, data, label) => ({
  type: 'bar',
  data: {
    labels: labels,
    datasets: [{
      label: label,
      data: data,
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
});"""

# Chart.js pie chart config
CHART_PIE_CONFIG = """// Chart.js pie chart configuration
const pieChartConfig = (labels, data) => ({
  type: 'pie',
  data: {
    labels: labels,
    datasets: [{
      data: data,
      backgroundColor: [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)'
      ]
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right'
      }
    }
  }
});"""

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

