"""Pre-built React + shadcn/ui component templates for rapid generation."""

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


# StatCard Template - KPI cards with Badge + Lucide trend arrows
STAT_CARD_TEMPLATE = ComponentTemplate(
    name="StatCard",
    category="card",
    description="KPI cards with Badge and Lucide trend indicators",
    tags=["kpi", "metric", "card", "stat"],
    data_requirements=["title", "value", "trend"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp } from "lucide-react"

interface KpiItem {
  title: string
  value: number | string
  trend?: string
}

interface Props {
  data?: KpiItem[]
}

const sampleData: KpiItem[] = [
  { title: "{{TITLE_1}}", value: 0, trend: "+{{TREND_1}}%" },
  { title: "{{TITLE_2}}", value: 0, trend: "+{{TREND_2}}%" },
  { title: "{{TITLE_3}}", value: "0.00" },
  { title: "{{TITLE_4}}", value: "-" },
]

const formatValue = (val: number | string) => {
  if (typeof val === "number") {
    if (val > 1000000) return "$" + (val / 1000000).toFixed(1) + "M"
    if (val > 1000) return "$" + (val / 1000).toFixed(1) + "K"
    return "$" + val.toFixed(0)
  }
  return String(val)
}

export default function StatCard({ data = sampleData }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Key Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.map((item, i) => (
            <div key={i} className="p-4 rounded-lg border">
              <p className="text-sm text-muted-foreground">{item.title}</p>
              <p className="text-2xl font-bold">{formatValue(item.value)}</p>
              {item.trend && (
                <Badge variant="secondary" className="mt-1">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  {item.trend}
                </Badge>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
''',
)


# DataTable Template - Filterable table using shadcn Table + Input
DATA_TABLE_TEMPLATE = ComponentTemplate(
    name="DataTable",
    category="table",
    description="Filterable and sortable data table with search",
    tags=["table", "data", "filter", "sort", "search"],
    data_requirements=["data_array", "columns"],
    code='''"use client"

import React, { useState, useMemo } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"

interface Props {
  data?: Record<string, unknown>[]
  title?: string
}

const sampleData = [
  { name: "Product A", category: "Electronics", price: 99, stock: 50 },
  { name: "Product B", category: "Home", price: 149, stock: 30 },
  { name: "Product C", category: "Sports", price: 79, stock: 100 },
]

export default function DataTable({ data = sampleData, title = "{{TABLE_TITLE}}" }: Props) {
  const [filter, setFilter] = useState("")
  const filtered = useMemo(() => {
    if (!filter) return data
    const f = filter.toLowerCase()
    return data.filter((item) =>
      JSON.stringify(item).toLowerCase().includes(f)
    )
  }, [data, filter])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <Input
          placeholder="Search..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              {{TABLE_HEADERS}}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((item, i) => (
              <TableRow key={i}>
                {{TABLE_CELLS}}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="text-sm text-muted-foreground mt-4">
          Showing {filtered.length} items
        </p>
      </CardContent>
    </Card>
  )
}
''',
)


# LineChart Template - Time series using Recharts LineChart
LINE_CHART_TEMPLATE = ComponentTemplate(
    name="LineChart",
    category="chart",
    description="Time series line chart for trends",
    tags=["chart", "line", "timeseries", "trend"],
    data_requirements=["date_field", "value_field"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface DataPoint {
  date: string
  value: number
}

interface Props {
  data?: DataPoint[]
  title?: string
}

const sampleData: DataPoint[] = [
  { date: "2024-01", value: 4000 },
  { date: "2024-02", value: 3000 },
  { date: "2024-03", value: 5000 },
  { date: "2024-04", value: 4500 },
  { date: "2024-05", value: 6000 },
]

export default function LineChartComponent({ data = sampleData, title = "{{CHART_TITLE}}" }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="hsl(var(--chart-1))" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
''',
)


# BarChart Template - Recharts BarChart
BAR_CHART_TEMPLATE = ComponentTemplate(
    name="BarChart",
    category="chart",
    description="Bar chart for comparisons",
    tags=["chart", "bar", "comparison"],
    data_requirements=["category_field", "value_field"],
    code='''"use client"

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
  { name: "A", value: 4000 },
  { name: "B", value: 3000 },
  { name: "C", value: 5000 },
  { name: "D", value: 4500 },
]

export default function BarChartComponent({ data = sampleData, title = "{{CHART_TITLE}}" }: Props) {
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
''',
)


# PieChart Template - Replaces DonutChart
PIE_CHART_TEMPLATE = ComponentTemplate(
    name="PieChart",
    category="chart",
    description="Pie chart for category breakdown",
    tags=["chart", "pie", "breakdown", "distribution"],
    data_requirements=["labels_field", "value_field"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from "recharts"

interface DataPoint {
  name: string
  value: number
}

interface Props {
  data?: DataPoint[]
  title?: string
}

const sampleData: DataPoint[] = [
  { name: "Cat A", value: 400 },
  { name: "Cat B", value: 300 },
  { name: "Cat C", value: 300 },
  { name: "Cat D", value: 200 },
]

const COLORS = ["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))"]

export default function PieChartComponent({ data = sampleData, title = "{{CHART_TITLE}}" }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              outerRadius={100}
              fill="hsl(var(--chart-1))"
              dataKey="value"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
''',
)


# AreaChart Template - Replaces HeatmapChart
AREA_CHART_TEMPLATE = ComponentTemplate(
    name="AreaChart",
    category="chart",
    description="Area chart for cumulative values",
    tags=["chart", "area", "cumulative", "intensity"],
    data_requirements=["date_field", "value_field"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface DataPoint {
  date: string
  value: number
}

interface Props {
  data?: DataPoint[]
  title?: string
}

const sampleData: DataPoint[] = [
  { date: "Jan", value: 4000 },
  { date: "Feb", value: 3000 },
  { date: "Mar", value: 5000 },
  { date: "Apr", value: 4500 },
  { date: "May", value: 6000 },
]

export default function AreaChartComponent({ data = sampleData, title = "{{CHART_TITLE}}" }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="value" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
''',
)


# ComposedChart Template - Replaces MixedChart
COMPOSED_CHART_TEMPLATE = ComponentTemplate(
    name="ComposedChart",
    category="chart",
    description="Combined line and bar chart",
    tags=["chart", "mixed", "line", "bar", "comparison"],
    data_requirements=["date_field", "line_field", "bar_field"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

interface DataPoint {
  date: string
  lineValue: number
  barValue: number
}

interface Props {
  data?: DataPoint[]
  title?: string
}

const sampleData: DataPoint[] = [
  { date: "Jan", lineValue: 4000, barValue: 2400 },
  { date: "Feb", lineValue: 3000, barValue: 1398 },
  { date: "Mar", lineValue: 5000, barValue: 3800 },
  { date: "Apr", lineValue: 4500, barValue: 3908 },
]

export default function ComposedChartComponent({ data = sampleData, title = "{{CHART_TITLE}}" }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="barValue" fill="hsl(var(--chart-1))" name="{{BAR_LABEL}}" />
            <Line type="monotone" dataKey="lineValue" stroke="hsl(var(--chart-2))" name="{{LINE_LABEL}}" />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
''',
)


# ListWithSearch Template - Card + Input + ScrollArea
LIST_WITH_SEARCH_TEMPLATE = ComponentTemplate(
    name="ListWithSearch",
    category="list",
    description="Searchable list with categories and badges",
    tags=["list", "search", "filter", "category"],
    data_requirements=["items_array", "name_field", "category_field"],
    code='''"use client"

import React, { useState, useMemo } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ListItem {
  name: string
  category: string
  price?: number
  stock?: number
}

interface Props {
  data?: ListItem[]
  title?: string
}

const sampleData: ListItem[] = [
  { name: "Product A", category: "Electronics", price: 99, stock: 50 },
  { name: "Product B", category: "Home", price: 149, stock: 30 },
  { name: "Product C", category: "Sports", price: 79, stock: 100 },
]

export default function ListWithSearch({ data = sampleData, title = "{{LIST_TITLE}}" }: Props) {
  const [filter, setFilter] = useState("")
  const filtered = useMemo(() => {
    if (!filter) return data
    const f = filter.toLowerCase()
    return data.filter(
      (item) =>
        item.name.toLowerCase().includes(f) ||
        item.category.toLowerCase().includes(f)
    )
  }, [data, filter])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <Input
          placeholder="Search..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="grid gap-4">
            {filtered.map((item, i) => (
              <div key={i} className="flex justify-between items-center p-4 border rounded-lg">
                <div>
                  <h3 className="font-semibold">{item.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {item.price ? `$${item.price}` : ""} {item.stock ? `- ${item.stock} in stock` : ""}
                  </p>
                </div>
                <Badge variant="secondary">{item.category}</Badge>
              </div>
            ))}
          </div>
        </ScrollArea>
        <p className="text-sm text-muted-foreground mt-4">
          Showing {filtered.length} of {data.length} items
        </p>
      </CardContent>
    </Card>
  )
}
''',
)


# MetricsDashboard Template - Multi-metric dashboard
METRICS_DASHBOARD_TEMPLATE = ComponentTemplate(
    name="MetricsDashboard",
    category="dashboard",
    description="Multi-metric dashboard with cards and chart",
    tags=["dashboard", "metrics", "kpi", "overview"],
    data_requirements=["metrics", "summary"],
    code='''"use client"

import React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Badge } from "@/components/ui/badge"

interface DataPoint {
  date: string
  value: number
}

interface Summary {
  total_revenue?: number
  total_orders?: number
  mrr?: number
  arr?: number
}

interface Props {
  metrics?: DataPoint[]
  summary?: Summary
  title?: string
}

const sampleMetrics: DataPoint[] = [
  { date: "Jan", value: 4000 },
  { date: "Feb", value: 3000 },
  { date: "Mar", value: 5000 },
  { date: "Apr", value: 4500 },
  { date: "May", value: 6000 },
]

const sampleSummary: Summary = { total_revenue: 27000, total_orders: 342 }

const formatCurrency = (val: number) => {
  if (val > 1000000) return "$" + (val / 1000000).toFixed(1) + "M"
  if (val > 1000) return "$" + (val / 1000).toFixed(1) + "K"
  return "$" + val.toFixed(0)
}

export default function MetricsDashboard({
  metrics = sampleMetrics,
  summary = sampleSummary,
  title = "{{DASHBOARD_TITLE}}",
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 border rounded-lg">
            <p className="text-sm text-muted-foreground">Revenue</p>
            <p className="text-2xl font-bold">
              {formatCurrency(summary.total_revenue ?? 0)}
            </p>
          </div>
          <div className="p-4 border rounded-lg">
            <p className="text-sm text-muted-foreground">Orders</p>
            <p className="text-2xl font-bold">{summary.total_orders ?? 0}</p>
          </div>
          <div className="p-4 border rounded-lg">
            <p className="text-sm text-muted-foreground">MRR</p>
            <p className="text-2xl font-bold">{formatCurrency(summary.mrr ?? 0)}</p>
          </div>
          <div className="p-4 border rounded-lg">
            <p className="text-sm text-muted-foreground">ARR</p>
            <p className="text-2xl font-bold">{formatCurrency(summary.arr ?? 0)}</p>
          </div>
        </div>
        <div>
          <h3 className="font-semibold mb-4">Trend Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
''',
)


# Collection of all templates
COMPONENT_TEMPLATES: Dict[str, ComponentTemplate] = {
    "StatCard": STAT_CARD_TEMPLATE,
    "DataTable": DATA_TABLE_TEMPLATE,
    "LineChart": LINE_CHART_TEMPLATE,
    "BarChart": BAR_CHART_TEMPLATE,
    "PieChart": PIE_CHART_TEMPLATE,
    "AreaChart": AREA_CHART_TEMPLATE,
    "ComposedChart": COMPOSED_CHART_TEMPLATE,
    "ListWithSearch": LIST_WITH_SEARCH_TEMPLATE,
    "MetricsDashboard": METRICS_DASHBOARD_TEMPLATE,
}


def get_template_by_name(name: str) -> Optional[ComponentTemplate]:
    """Get a template by name."""
    return COMPONENT_TEMPLATES.get(name)


def list_templates(
    category: Optional[str] = None, tags: Optional[List[str]] = None
) -> List[ComponentTemplate]:
    """List templates, optionally filtered by category or tags."""
    templates = list(COMPONENT_TEMPLATES.values())

    if category:
        templates = [t for t in templates if t.category == category]

    if tags:
        templates = [t for t in templates if any(tag in t.tags for tag in tags)]

    return templates
