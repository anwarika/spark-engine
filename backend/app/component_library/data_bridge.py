"""Data bridge utilities and templates for sample->real data swapping."""

from typing import Any, Dict, List

# Boilerplate for wrapping component with DataProvider (used when generating custom components)
DATA_BRIDGE_WRAPPER = """
// Data Bridge: Component consumes data via context
import { useContext } from 'solid-js';

const DataContext = window.DataContext;
function useDashboardData() {
  const ctx = useContext(DataContext);
  return ctx ? { data: ctx.data, mode: ctx.mode } : { data: () => null, mode: () => 'sample' };
}
"""

# Expected keys by template type (for validation)
TEMPLATE_DATA_REQUIREMENTS: Dict[str, List[str]] = {
    "StatCard": ["summary"],
    "DataTable": ["products", "users", "sales", "accounts", "opportunities"],  # union by profile
    "LineChart": ["metrics"],
    "BarChart": ["products", "metrics", "accounts"],
    "DonutChart": ["products", "accounts"],
    "ListWithSearch": ["products", "items"],
    "MetricsDashboard": ["metrics", "summary", "orders", "events"],
    "HeatmapChart": ["metrics"],
    "MixedChart": ["metrics"],
}


def get_expected_keys_for_template(template_name: str, profile: str = "ecommerce") -> List[str]:
    """Return expected top-level keys for a template+profile combo."""
    defaults = {
        "ecommerce": ["products", "metrics", "summary", "orders", "sales"],
        "saas": ["accounts", "metrics", "summary", "events", "subscriptions"],
        "sales": ["opportunities", "metrics", "accounts"],
        "marketing": ["campaigns", "metrics", "leads"],
        "finance": ["transactions", "pnl_monthly", "metrics"],
    }
    base = defaults.get(profile, defaults["ecommerce"])
    # Add template-specific requirements
    extra = TEMPLATE_DATA_REQUIREMENTS.get(template_name, [])
    return list(dict.fromkeys(base + extra))
