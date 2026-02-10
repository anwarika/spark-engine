# Migration Guide: Spark v1.x → v2.0

This guide helps you upgrade from Spark v1.x (Chart.js) to v2.0 (ApexCharts + Data Bridge).

## Breaking Changes

### 1. Chart.js Removed → ApexCharts Added

**What Changed:**
- Chart.js is no longer loaded in the iframe
- ApexCharts v3.54.1 is now the standard charting library
- All chart templates use ApexCharts API

**Impact:**
- Components generated with v1.x that use `window.Chart` will break
- Custom components importing `chart.js` will fail validation

**Action Required:**

**Option A: Regenerate Components (Recommended)**

Simply regenerate your components through the chat interface. They'll automatically use ApexCharts.

**Option B: Manual Migration**

If you have custom chart code, migrate it:

```javascript
// OLD (Chart.js)
import { createResource, onMount } from 'solid-js';

export default function MyChart() {
  const [data] = createResource(fetchData);
  let canvasRef;
  
  onMount(() => {
    const ctx = canvasRef.getContext('2d');
    new window.Chart(ctx, {
      type: 'line',
      data: { labels: [...], datasets: [...] },
      options: { responsive: true }
    });
  });
  
  return <canvas ref={canvasRef}></canvas>;
}
```

```javascript
// NEW (ApexCharts)
import { createResource, createEffect, onCleanup } from 'solid-js';
import ApexCharts from 'apexcharts';

export default function MyChart() {
  const [data] = createResource(fetchData);
  let chartRef;
  let chartInstance;
  
  createEffect(function() {
    if (!data() || !chartRef) return;
    const options = {
      chart: { type: 'line', toolbar: { show: false } },
      series: [{ name: 'Data', data: [...] }],
      xaxis: { categories: [...] }
    };
    if (chartInstance) chartInstance.destroy();
    chartInstance = new ApexCharts(chartRef, options);
    chartInstance.render();
  });
  
  onCleanup(function() {
    if (chartInstance) chartInstance.destroy();
  });
  
  return <div ref={chartRef}></div>;
}
```

**Key Differences:**

| Chart.js | ApexCharts |
|----------|------------|
| `<canvas ref={ref}>` | `<div ref={ref}>` |
| `onMount()` with manual data check | `createEffect()` for reactivity |
| `ctx.getContext('2d')` | Direct element ref |
| `new Chart(ctx, config)` | `new ApexCharts(el, config)` |
| No cleanup needed | Call `chart.destroy()` in `onCleanup()` |

### 2. New Data Bridge Pattern

**What's New:**
- Components can now swap between sample (mock) and real data without regeneration
- `window.__DATA_MODE` tracks current mode (`'sample'` or `'real'`)
- POST `/api/components/{id}/data/swap` stores real data server-side

**Impact:**
- Components generated with v1.x will still work but won't support data swapping
- New components automatically support the data bridge

**How to Use:**

**Step 1: Store Real Data**
```bash
curl -X POST http://localhost:8000/api/components/{component_id}/data/swap \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "real",
    "data": {
      "products": [...],
      "metrics": [...],
      "summary": {...}
    }
  }'
```

**Step 2: Trigger Swap**

From the frontend, click the **Sample/Real toggle** in the iframe component, OR programmatically:

```typescript
// In React parent component
iframeRef.current?.contentWindow?.postMessage(
  { type: 'data_swap', mode: 'real' },
  '*'
);
```

**Step 3: Component Refetches**

The component automatically refetches from `/api/components/{id}/data` with `data_mode: 'real'` and displays your real data.

**For Custom Components:**

Update your `fetchData` to support the data bridge:

```javascript
async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      mock: { profile: 'ecommerce', scale: 'medium' }, 
      data_mode: dataMode 
    })
  });
  return response.json();
}

// Use reactive source for auto-refetch on mode change
const [apiData] = createResource(
  function() { return window.__DATA_MODE || 'sample'; }, 
  fetchData
);
```

### 3. New Component Templates

**What's New:**
- 9 templates (was 6)
- Added: `DonutChart`, `HeatmapChart`, `MixedChart`

**Impact:**
- No breaking changes - purely additive

**Usage:**
```
"Show me a donut chart of sales by category"
"Create a heatmap of activity over the last 90 days"
"Compare revenue and orders in a mixed chart"
```

## Updated Dependencies

### Backend (Python)

No new Python dependencies. ApexCharts is loaded via CDN.

```diff
# backend/requirements.txt (no changes)
```

### Compiler Workspace

The `/tmp/spark-compiler/package.json` is updated automatically:

```diff
{
  "dependencies": {
    "solid-js": "^1.8.7",
    "babel-preset-solid": "^1.8.16",
    "@babel/core": "^7.24.0",
    "@babel/cli": "^7.24.0",
-   "apexcharts": "^4.2.0",
-   "chart.js": "^4.4.1"
+   "apexcharts": "^3.54.1"
  }
}
```

### Frontend (React)

No frontend dependency changes. ApexCharts is used only in generated components (loaded via CDN).

## Database Schema

No schema changes. Existing components continue to work.

## API Changes

### New Endpoints

**POST `/api/components/{id}/data/swap`**

Store real data for a component to enable sample→real swap.

**Request Body:**
```json
{
  "mode": "real",
  "data": {
    "products": [...],
    "metrics": [...],
    "summary": {...}
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "mode": "real"
}
```

**Stored in Redis:**
- Key: `databridge:{tenant_id}:{component_id}:real`
- TTL: 1 hour
- Format: JSON string

### Modified Endpoints

**POST `/api/components/{id}/data`**

Now accepts optional `data_mode` parameter:

**Request Body (v2.0):**
```json
{
  "mock": {
    "profile": "ecommerce",
    "scale": "medium",
    "days": 180
  },
  "data_mode": "real"
}
```

When `data_mode: "real"` is sent:
1. Backend checks Redis for stored real data
2. Returns real data if found
3. Falls back to mock data if not found

**Backward Compatible:** If `data_mode` is omitted, defaults to `"sample"` (mock data).

## Testing Your Migration

### 1. Start Spark v2.0

```bash
docker-compose up --build
```

### 2. Generate a New Component

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-User-ID: test-user" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a line chart of revenue over time"}'
```

You should see a modern ApexCharts line chart with smooth curves and gradient fill.

### 3. Test Data Bridge

```bash
# Store real data
curl -X POST http://localhost:8000/api/components/{component_id}/data/swap \
  -H "X-Tenant-ID: test-tenant" \
  -d '{
    "mode": "real",
    "data": {
      "metrics": [
        {"date": "2026-01-01", "revenue": 10000},
        {"date": "2026-01-02", "revenue": 12000},
        {"date": "2026-01-03", "revenue": 15000}
      ]
    }
  }'

# Response: {"status": "ok", "mode": "real"}
```

Then click the **Real** toggle in the UI - the chart should update with your real data.

### 4. Verify Templates

All 9 templates should be available:

```bash
curl http://localhost:8000/api/catalog/templates \
  -H "X-Tenant-ID: test-tenant"
```

## Rollback Plan

If you need to rollback to v1.x (Chart.js):

```bash
git checkout v1.0.0
docker-compose down
docker-compose up --build
```

**Data Compatibility:** Components stored in the database will remain but chart components won't render without Chart.js.

## Support

- **GitHub Issues**: Report bugs at https://github.com/your-org/spark/issues
- **Discussions**: Ask questions at https://github.com/your-org/spark/discussions
- **Discord**: Join our community (link in README)

## What's Next?

See [ROADMAP.md](ROADMAP.md) for upcoming features:
- Real-time data streaming support
- Chart theming system
- Component composition (nested templates)
- GraphQL data source support
