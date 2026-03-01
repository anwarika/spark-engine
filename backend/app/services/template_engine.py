"""Template matching and composition engine for rapid component generation."""

import logging
import re
from typing import Dict, List, Optional

from app.component_library.templates import (
    COMPONENT_TEMPLATES,
    ComponentTemplate,
    list_templates,
)

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Matches user prompts to pre-built templates and composes components.
    This enables faster generation by using templates instead of full LLM generation.
    """

    def __init__(self):
        self.templates = COMPONENT_TEMPLATES

    def match_templates(self, user_prompt: str) -> List[ComponentTemplate]:
        """
        Match user prompt to relevant templates based on keywords and intent.
        Returns list of matching templates, sorted by relevance.
        """
        prompt_lower = user_prompt.lower()
        matches = []

        for template in self.templates.values():
            score = 0
            
            # Check category keywords
            if template.category in prompt_lower:
                score += 10
            
            # Check tags
            for tag in template.tags:
                if tag in prompt_lower:
                    score += 5
            
            # Check specific keywords
            if template.name.lower() in prompt_lower:
                score += 20
            
            # Chart-specific matching
            if template.category == "chart":
                chart_keywords = ["show", "visualize", "display", "plot", "graph", "trend"]
                for keyword in chart_keywords:
                    if keyword in prompt_lower:
                        score += 3
            
            # Table-specific matching
            if template.category == "table":
                table_keywords = ["list", "table", "rows", "data", "all"]
                for keyword in table_keywords:
                    if keyword in prompt_lower:
                        score += 3
            
            # Dashboard-specific matching
            if template.category == "dashboard":
                dashboard_keywords = ["overview", "summary", "dashboard", "metrics", "kpi"]
                for keyword in dashboard_keywords:
                    if keyword in prompt_lower:
                        score += 3
            
            if score > 0:
                matches.append((score, template))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return [template for score, template in matches]

    def should_use_template(self, user_prompt: str) -> bool:
        """
        Determine if we should use a template vs full LLM generation.
        Returns True if a good template match is found.
        """
        matches = self.match_templates(user_prompt)
        if not matches:
            return False
        
        # Use template if we have a strong match
        # This is a simple heuristic - could be improved with ML
        prompt_lower = user_prompt.lower()
        
        # Strong indicators for template use
        template_indicators = [
            "show me", "display", "list", "table of", "chart", "graph",
            "dashboard", "overview", "metrics", "kpis", "summary"
        ]
        
        for indicator in template_indicators:
            if indicator in prompt_lower:
                return True
        
        return False

    def detect_data_profile(self, user_prompt: str) -> str:
        """
        Detect which data profile to use based on prompt content.
        Returns one of: ecommerce, saas, marketing, finance, sales
        """
        prompt_lower = user_prompt.lower()
        
        # SaaS indicators
        saas_keywords = ["mrr", "arr", "churn", "retention", "subscription", "trial", "activation"]
        if any(keyword in prompt_lower for keyword in saas_keywords):
            return "saas"
        
        # Marketing indicators
        marketing_keywords = ["campaign", "ad", "spend", "impression", "click", "lead", "attribution"]
        if any(keyword in prompt_lower for keyword in marketing_keywords):
            return "marketing"
        
        # Finance indicators
        finance_keywords = ["revenue", "expense", "profit", "margin", "ebitda", "p&l", "pnl"]
        if any(keyword in prompt_lower for keyword in finance_keywords):
            return "finance"
        
        # Sales indicators
        sales_keywords = ["pipeline", "opportunity", "deal", "quota", "booking", "forecast"]
        if any(keyword in prompt_lower for keyword in sales_keywords):
            return "sales"
        
        # Default to ecommerce
        return "ecommerce"

    def fill_template(
        self, template: ComponentTemplate, user_prompt: str, params: Optional[Dict] = None
    ) -> str:
        """
        Fill a template with user-specific data and parameters.
        Performs basic variable substitution.
        """
        code = template.code
        
        # Detect and inject profile
        profile = self.detect_data_profile(user_prompt)
        code = code.replace("{{PROFILE}}", profile)
        
        # If params provided, use them for substitution
        if params:
            for key, value in params.items():
                placeholder = f"{{{{{key}}}}}"
                code = code.replace(placeholder, str(value))
        
        # Default substitutions based on template type
        if template.name == "StatCard":
            code = self._fill_stat_card(code, user_prompt, profile)
        elif template.name == "DataTable":
            code = self._fill_data_table(code, user_prompt, profile)
        elif template.name == "LineChart":
            code = self._fill_line_chart(code, user_prompt, profile)
        elif template.name == "BarChart":
            code = self._fill_bar_chart(code, user_prompt, profile)
        elif template.name == "ListWithSearch":
            code = self._fill_list(code, user_prompt, profile)
        elif template.name == "MetricsDashboard":
            code = self._fill_dashboard(code, user_prompt, profile)
        elif template.name == "PieChart":
            code = self._fill_pie_chart(code, user_prompt, profile)
        elif template.name == "AreaChart":
            code = self._fill_area_chart(code, user_prompt, profile)
        elif template.name == "ComposedChart":
            code = self._fill_composed_chart(code, user_prompt, profile)
        
        return code

    def _fill_stat_card(self, code: str, prompt: str, profile: str) -> str:
        """Fill StatCard template with sensible defaults."""
        # Profile-specific defaults
        if profile == "saas":
            return code.replace("{{TITLE_1}}", "MRR").replace("{{VALUE_1}}", "mrr") \
                .replace("{{TREND_1}}", "12") \
                .replace("{{TITLE_2}}", "Active Accounts").replace("{{VALUE_2}}", "active_accounts") \
                .replace("{{TREND_2}}", "5") \
                .replace("{{TITLE_3}}", "Churn Rate").replace("{{VALUE_3}}", "churn_rate") \
                .replace("{{TITLE_4}}", "Net Retention").replace("{{VALUE_4}}", "net_retention")
        elif profile == "sales":
            return code.replace("{{TITLE_1}}", "Pipeline").replace("{{VALUE_1}}", "pipeline_amount") \
                .replace("{{TREND_1}}", "8") \
                .replace("{{TITLE_2}}", "Open Opps").replace("{{VALUE_2}}", "open_opps") \
                .replace("{{TREND_2}}", "15") \
                .replace("{{TITLE_3}}", "Win Rate").replace("{{VALUE_3}}", "win_rate") \
                .replace("{{TITLE_4}}", "Bookings").replace("{{VALUE_4}}", "bookings_total")
        else:  # ecommerce default
            return code.replace("{{TITLE_1}}", "Revenue").replace("{{VALUE_1}}", "total_revenue") \
                .replace("{{TREND_1}}", "15") \
                .replace("{{TITLE_2}}", "Orders").replace("{{VALUE_2}}", "total_orders") \
                .replace("{{TREND_2}}", "8") \
                .replace("{{TITLE_3}}", "AOV").replace("{{VALUE_3}}", "avg_order_value") \
                .replace("{{TITLE_4}}", "Active Users").replace("{{VALUE_4}}", "active_users")

    def _fill_data_table(self, code: str, prompt: str, profile: str) -> str:
        """Fill DataTable template with sensible defaults."""
        if profile == "saas":
            return code.replace("{{TABLE_TITLE}}", "Accounts").replace(
                "{{TABLE_HEADERS}}",
                "<TableHead>Name</TableHead><TableHead>Segment</TableHead><TableHead>Region</TableHead><TableHead>Status</TableHead>",
            ).replace(
                "{{TABLE_CELLS}}",
                "<TableCell>{item.name}</TableCell><TableCell><Badge variant=\"secondary\">{item.segment}</Badge></TableCell><TableCell>{item.region}</TableCell><TableCell>{item.status}</TableCell>",
            )
        elif profile == "sales":
            return code.replace("{{TABLE_TITLE}}", "Opportunities").replace(
                "{{TABLE_HEADERS}}",
                "<TableHead>ID</TableHead><TableHead>Account</TableHead><TableHead>Amount</TableHead><TableHead>Stage</TableHead>",
            ).replace(
                "{{TABLE_CELLS}}",
                "<TableCell>{item.id}</TableCell><TableCell>{item.account_id}</TableCell><TableCell>${item.amount?.toFixed(0)}</TableCell><TableCell><Badge variant=\"secondary\">{item.stage}</Badge></TableCell>",
            )
        else:  # ecommerce
            return code.replace("{{TABLE_TITLE}}", "Products").replace(
                "{{TABLE_HEADERS}}",
                "<TableHead>Product</TableHead><TableHead>Category</TableHead><TableHead>Price</TableHead><TableHead>Stock</TableHead>",
            ).replace(
                "{{TABLE_CELLS}}",
                "<TableCell>{item.name}</TableCell><TableCell><Badge variant=\"secondary\">{item.category}</Badge></TableCell><TableCell>${item.price}</TableCell><TableCell>{item.stock}</TableCell>",
            )

    def _fill_line_chart(self, code: str, prompt: str, profile: str) -> str:
        """Fill LineChart template."""
        if profile == "saas":
            return code.replace("{{CHART_TITLE}}", "MRR Trend") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{VALUE_FIELD}}", "mrr") \
                .replace("{{METRIC_LABEL}}", "MRR")
        else:
            return code.replace("{{CHART_TITLE}}", "Revenue Trend") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{VALUE_FIELD}}", "revenue") \
                .replace("{{METRIC_LABEL}}", "Revenue")

    def _fill_bar_chart(self, code: str, prompt: str, profile: str) -> str:
        """Fill BarChart template."""
        if profile == "ecommerce":
            return code.replace("{{CHART_TITLE}}", "Top Products") \
                .replace("{{DATA_ARRAY}}", "products") \
                .replace("{{CATEGORY_FIELD}}", "name") \
                .replace("{{VALUE_FIELD}}", "price") \
                .replace("{{VALUE_LABEL}}", "Price")
        else:
            return code.replace("{{CHART_TITLE}}", "Performance Comparison") \
                .replace("{{DATA_ARRAY}}", "metrics") \
                .replace("{{CATEGORY_FIELD}}", "date") \
                .replace("{{VALUE_FIELD}}", "revenue") \
                .replace("{{VALUE_LABEL}}", "Revenue")

    def _fill_pie_chart(self, code: str, prompt: str, profile: str) -> str:
        """Fill PieChart template."""
        if profile == "ecommerce":
            return code.replace("{{CHART_TITLE}}", "Sales by Category") \
                .replace("{{DATA_ARRAY}}", "products") \
                .replace("{{CATEGORY_FIELD}}", "category") \
                .replace("{{VALUE_FIELD}}", "price")
        elif profile == "saas":
            return code.replace("{{CHART_TITLE}}", "MRR by Segment") \
                .replace("{{DATA_ARRAY}}", "accounts") \
                .replace("{{CATEGORY_FIELD}}", "segment") \
                .replace("{{VALUE_FIELD}}", "mrr")
        else:
            return code.replace("{{CHART_TITLE}}", "Breakdown") \
                .replace("{{DATA_ARRAY}}", "products") \
                .replace("{{CATEGORY_FIELD}}", "category") \
                .replace("{{VALUE_FIELD}}", "price")

    def _fill_area_chart(self, code: str, prompt: str, profile: str) -> str:
        """Fill AreaChart template."""
        if profile == "saas":
            return code.replace("{{CHART_TITLE}}", "MRR Intensity") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{VALUE_FIELD}}", "mrr") \
                .replace("{{METRIC_LABEL}}", "MRR")
        else:
            return code.replace("{{CHART_TITLE}}", "Revenue Intensity") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{VALUE_FIELD}}", "revenue") \
                .replace("{{METRIC_LABEL}}", "Revenue")

    def _fill_composed_chart(self, code: str, prompt: str, profile: str) -> str:
        """Fill ComposedChart template."""
        if profile == "saas":
            return code.replace("{{CHART_TITLE}}", "MRR vs Churn") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{LINE_FIELD}}", "mrr") \
                .replace("{{BAR_FIELD}}", "churned_accounts") \
                .replace("{{LINE_LABEL}}", "MRR") \
                .replace("{{BAR_LABEL}}", "Churned")
        else:
            return code.replace("{{CHART_TITLE}}", "Revenue vs Orders") \
                .replace("{{DATE_FIELD}}", "date") \
                .replace("{{LINE_FIELD}}", "revenue") \
                .replace("{{BAR_FIELD}}", "conversions") \
                .replace("{{LINE_LABEL}}", "Revenue") \
                .replace("{{BAR_LABEL}}", "Conversions")

    def _fill_list(self, code: str, prompt: str, profile: str) -> str:
        """Fill ListWithSearch template."""
        if profile == "ecommerce":
            return code.replace("{{LIST_TITLE}}", "Products")
        else:
            return code.replace("{{LIST_TITLE}}", "Items")

    def _fill_dashboard(self, code: str, prompt: str, profile: str) -> str:
        """Fill MetricsDashboard template."""
        if profile == "saas":
            return code.replace("{{DASHBOARD_TITLE}}", "SaaS Metrics")
        else:
            return code.replace("{{DASHBOARD_TITLE}}", "Dashboard")

    async def generate_from_template(self, user_prompt: str) -> Optional[str]:
        """
        Generate a component from a template if possible.
        Returns None if no suitable template found.
        """
        matches = self.match_templates(user_prompt)
        if not matches:
            return None
        
        # Use the best matching template
        best_template = matches[0]
        logger.info(f"Using template: {best_template.name} for prompt: {user_prompt[:50]}...")
        
        return self.fill_template(best_template, user_prompt)

