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


def _llm_config_from_settings() -> LLMConfig:
    """Build LLMConfig from application settings."""
    # Map anthropic -> openrouter (OpenRouter supports Anthropic models)
    provider = settings.llm_provider
    model = settings.llm_model
    api_key = settings.llm_api_key
    if provider == "anthropic":
        provider = "openrouter"
        model = getattr(settings, "anthropic_model", "claude-3-opus-20240229")
        api_key = api_key or settings.openrouter_api_key
    elif provider == "openai" and not api_key:
        api_key = settings.openai_api_key
    elif provider == "openrouter" and not api_key:
        api_key = settings.openrouter_api_key

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        fallback_provider=settings.llm_fallback_provider,
        fallback_model=settings.llm_fallback_model,
        fallback_api_key=settings.llm_fallback_api_key,
        fallback_base_url=settings.llm_fallback_base_url,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
    )


def _llm_config_from_dict(data: Dict[str, Any]) -> LLMConfig:
    """Build LLMConfig from per-request override dict."""
    return LLMConfig(
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key"),
        base_url=data.get("base_url"),
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 4096),
    )


class LLMService:
    def __init__(self):
        self.prompt_cache = PromptCache()
        self.gateway = LLMGateway(_llm_config_from_settings())

        self.system_prompt = """You are Spark, an AI micro-app generator. When asked to create a visualization or interactive component, you generate a single-file React component.

TECH STACK (use ONLY these):
- React 18+ (hooks only, no class components)
- shadcn/ui components (Card, Table, Badge, Button, Tabs, etc.)
- Recharts for all charts (BarChart, LineChart, AreaChart, PieChart, RadarChart, etc.)
- Tailwind CSS for styling
- Lucide React for icons

AVAILABLE PRE-BUILT TEMPLATES (use when appropriate for faster, optimized generation):
1. StatCard - KPI cards with Badge + Lucide trend arrows (for: metrics, kpis, summary stats)
2. DataTable - Filterable/sortable tables using shadcn Table + Input (for: listing data, tables, browsing records)
3. LineChart - Time series using Recharts LineChart in Card (for: trends over time, line graphs)
4. BarChart - Comparison using Recharts BarChart in Card (for: comparing values, bar graphs)
5. PieChart - Category breakdown using Recharts PieChart (for: distributions, breakdowns)
6. AreaChart - Cumulative values using Recharts AreaChart (for: activity, intensity over time)
7. ComposedChart - Mixed line + bar using Recharts ComposedChart (for: comparing two metrics)
8. ListWithSearch - Searchable list using Card + Input + ScrollArea (for: browsing items, directories)
9. MetricsDashboard - Multi-metric dashboard composing multiple chart types (for: dashboards, overviews, multiple KPIs)

WHEN TO USE TEMPLATES:
- User asks to "show", "display", "list", "chart" data → Use matching template
- Request mentions "dashboard", "overview", "metrics" → Use MetricsDashboard
- Request is for specific data visualization → Use corresponding chart template
- Templates are pre-optimized and compile faster than custom code

COMPONENT STRUCTURE:
- Export a single default function component
- Accept a `data` prop for dynamic data (use TypeScript interface)
- Include realistic sample data as default prop values
- Use shadcn/ui Card as the outer wrapper
- All components must be self-contained in a single file

AVAILABLE SHADCN/UI COMPONENTS:
Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
Table, TableHeader, TableBody, TableRow, TableHead, TableCell
Badge, Button, Input, Label, Select, Tabs, TabsList, TabsTrigger, TabsContent
Separator, ScrollArea, Tooltip, Dialog, Popover, DropdownMenu
Alert, AlertTitle, AlertDescription

AVAILABLE RECHARTS COMPONENTS:
BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell
RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
ComposedChart, ScatterChart, Scatter, Treemap
XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer

COLOR PALETTE (use CSS variables):
--chart-1 through --chart-5 for chart colors
Use Tailwind color classes for non-chart elements

RULES:
1. NO fetch/XMLHttpRequest/WebSocket — data comes via props or sample data
2. NO localStorage/sessionStorage/document/window access
3. NO dynamic imports or eval
4. NO external CDN scripts
5. Always wrap charts in <ResponsiveContainer width="100%" height={300}>
6. Always use "use client" directive at top of file
7. Use TypeScript syntax for prop interfaces
8. Handle empty/null data gracefully with fallback UI

DATA BRIDGE (sample to real swap):
- Data is passed via props. Parent can inject real data via postMessage { type: 'spark_data', payload: {...} }.
- Include realistic sample data as default prop values.
- Component re-renders when parent sends spark_data with new payload.

TEMPLATE EXAMPLE:

"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface DataPoint {
  name: string
  value: number
}

interface Props {
  data?: DataPoint[]
  title?: string
}

const sampleData: DataPoint[] = [
  { name: "Q1", value: 4000 },
  { name: "Q2", value: 3000 },
  { name: "Q3", value: 5000 },
  { name: "Q4", value: 4500 },
]

export default function MetricsChart({ data = sampleData, title = "Quarterly Revenue" }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

Decision guidance:
- Assess whether the user request matches a pre-built template pattern. If so, prefer template-based generation.
- For custom visualizations or unique UX requirements, generate custom components.
- If the query is purely conversational or explanatory, respond with text.
- When you choose to return a component, include reasoning for why a visual representation was preferable and which approach you chose.

Response format (IMPORTANT: Return raw code in the content field, NO markdown code fences):
{
  "type": "text" or "component",
  "content": "<your response or raw React TSX code WITHOUT markdown fences>",
  "reasoning": "<brief explanation of your choice>"
}

Respond only with valid JSON in the specified format. CRITICAL: Do NOT wrap code in markdown fences."""
        self.style_doc_path = Path(__file__).resolve().parents[1] / "static" / "daisyui.txt"
        self._style_doc_content = ""
        self._style_doc_mtime = 0.0
        self._style_cache_max_length = 8000

    def _clean_component_code(self, content: str) -> str:
        """Fully normalise LLM-generated component code.

        Problems the LLM causes:
        1. Double-escapes newlines: the JSON content field contains literal \\n
           (backslash + n) instead of real newlines.  After json.loads these
           arrive as chr(92)+chr(110) in the Python string.
        2. Malformed "use client" directive — missing/extra quotes.
        3. Markdown code fences wrapping the code.
        """
        # ── Step 1: decode double-escaped newlines ──────────────────────────
        # Detect: has literal \\ + n (two chars) but no real newline char.
        BACKSLASH_N = chr(92) + chr(110)   # \ n
        REAL_NEWLINE = chr(10)             # \n
        if BACKSLASH_N in content and REAL_NEWLINE not in content:
            content = (content
                       .replace(chr(92) + chr(110), chr(10))   # \n
                       .replace(chr(92) + chr(116), chr(9))    # \t
                       .replace(chr(92) + chr(114), chr(13))   # \r
                       .replace(chr(92) + chr(34),  chr(34))   # \"
                       )

        # ── Step 2: strip markdown code fences ──────────────────────────────
        content = re.sub(r'^```[\w]*\n?', '', content.strip(), flags=re.MULTILINE)
        content = re.sub(r'\n?```$', '', content.strip(), flags=re.MULTILINE)
        content = content.strip()

        # ── Step 3: normalise "use client" directive ─────────────────────────
        stripped = content.lstrip()
        leading = content[: len(content) - len(stripped)]

        # Double closing quote: "use client""
        if stripped.startswith('"use client""'):
            content = leading + '"use client"' + stripped[13:]
        # Missing opening quote: use client"
        elif stripped.startswith('use client"'):
            content = leading + '"use client"' + stripped[11:]
        # No quotes: use client\n  or  use client (EOF)
        elif re.match(r'use client[\r\n]', stripped) or stripped == 'use client':
            after = stripped[len('use client'):]
            content = leading + '"use client"' + after

        return content

    # Keep old names as thin wrappers for any code that calls them directly.
    def _strip_markdown_fences(self, content: str) -> str:
        content = re.sub(r'^```[\w]*\n?', '', content.strip(), flags=re.MULTILINE)
        content = re.sub(r'\n?```$', '', content.strip(), flags=re.MULTILINE)
        return content.strip()

    def _fix_use_client_directive(self, content: str) -> str:
        return self._clean_component_code(content)

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

    async def _call_gateway(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        gateway: LLMGateway,
        **kwargs,
    ) -> ChatResponse:
        """Call gateway and parse response into ChatResponse."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await gateway.chat(
            full_messages,
            response_format={"type": "json_object"},
            **kwargs,
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        return ChatResponse(
            type=parsed.get("type", "text"),
            content=parsed.get("content", ""),
            reasoning=parsed.get("reasoning", ""),
        )

    async def analyze(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        provider_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ChatResponse:
        """Direct LLM call for analysis (e.g. A2A negotiation). Returns ChatResponse."""
        gateway = self.gateway
        if provider_config:
            gateway = LLMGateway(_llm_config_from_dict(provider_config))
        return await self._call_gateway(messages, system_prompt, gateway, **kwargs)

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        provider_config: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        if conversation_history is None:
            conversation_history = []

        # Per-request LLM override
        gateway = self.gateway
        if provider_config:
            gateway = LLMGateway(_llm_config_from_dict(provider_config))

        # Check prompt cache first
        cached_response = await self.prompt_cache.get_cached_response(
            user_message, "general"
        )
        if cached_response:
            logger.info("Using cached LLM response")
            if cached_response.type == "component":
                cached_response.content = self._fix_use_client_directive(cached_response.content)
            return cached_response

        self._refresh_style_reference()
        style_snippet = self._get_style_reference_snippet()
        system_prompt = self.system_prompt
        if style_snippet:
            system_prompt = f"{system_prompt}\n\nStyle reference (cached):\n{style_snippet}"

        messages = conversation_history + [{"role": "user", "content": user_message}]

        try:
            response = await self._call_gateway(messages, system_prompt, gateway)

            # Normalise code content (decode newlines, strip fences, fix "use client")
            if response.type == "component":
                response.content = self._clean_component_code(response.content)

            # Cache the response
            await self.prompt_cache.cache_response(user_message, "general", response)

            return response

        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return ChatResponse(
                type="text",
                content=f"I apologize, but I encountered an error: {str(e)}",
                reasoning="Error fallback",
            )

    @property
    def model(self):
        return self.gateway.config.model
