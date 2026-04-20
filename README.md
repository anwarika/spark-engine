# Spark

### Headless Micro App Generation Engine

Spark turns natural language prompts into live, embeddable micro-apps. Your AI agent sends a prompt — Spark generates, compiles, and serves a sandboxed Solid.js UI as an iframe URL. Any chat interface can embed Spark. No UI framework required.

[![Version](https://img.shields.io/badge/version-3.4.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-AGPLv3-green.svg)](LICENSE)
[![SDK](https://img.shields.io/badge/npm-%40spark--engine%2Fsdk-cb0000.svg)](packages/spark-sdk)

---

## What it does

Your agent sends a prompt like _"Build a sales pipeline dashboard for my Q1 deals"_. Spark:

1. Calls the LLM with your prompt and optional data context
2. Validates, compiles, and bundles the generated Solid.js component
3. Returns an `iframe_url` your app can render immediately
4. Persists the component so the user can pin it, revisit it, and regenerate it

**Headless by design.** Spark has no opinions about your UI shell, design system, or chat framework. You own the chrome — Spark owns the generation.

---

## Demo

### Executive Intelligence Dashboard

Prompt: `"Build an executive dashboard — ARR with sparklines, revenue trend by type, pipeline funnel, regional breakdown, and CAC vs LTV trend"`

Real ApexCharts: stacked bar chart, donut segmentation, horizontal funnel, CAC/LTV dual-line, sparkline KPI cards — all interactive with shared tooltips.

![Executive Dashboard](docs/screenshots/rich-executive.png)

---

### Platform Observability

Prompt: `"Show me a platform observability dashboard — uptime, error rate, p50/p95/p99 latency chart with SLO annotation, service health table, error heatmap, and volume trends"`

![Platform Observability](docs/screenshots/rich-observability.png)

---

### Product Analytics

Prompt: `"Give me a product analytics dashboard — DAU/WAU/MAU trend with 7-day moving average, cohort retention heatmap, acquisition channels donut, and activation funnel"`

![Product Analytics](docs/screenshots/rich-product.png)

---

### API — Generate, Pin, Regenerate

The headless REST API and `@spark-engine/sdk` in action — generating a micro-app, pinning it to a stable ID, and regenerating it with a new prompt.

![API Demo](docs/screenshots/screenshot-api.png)

---

## Quick Start

```bash
git clone https://github.com/your-org/spark.git
cd spark
cp .env.example .env   # add OPENAI_API_KEY at minimum
docker-compose up -d
```

Backend runs at `http://localhost:8000`. Frontend dev server at `http://localhost:5173`.

---

## Core Concepts

### Generate → Pin → Regenerate

```
Prompt  ──▶  /api/a2a/generate  ──▶  component_id + iframe_url
                                              │
                                   /api/apps/pin  ──▶  pin_id (stable bookmark)
                                              │
                               /api/apps/{pin_id}/regenerate  ──▶  new component_id
                                              │                       (same pin_id)
                                   user navigates by slot_name, always gets latest
```

**Pin ID is the stable identity.** The `component_id` underneath can be swapped on every regeneration — the user's bookmark (`slot_name`) never breaks.

### Event Protocol

Every Spark iframe emits structured `spark:*` postMessage events. Your host subscribes to them:

```javascript
window.addEventListener('message', (e) => {
  if (e.data?.type === 'spark:pinned') {
    // user clicked "Pin" inside the micro-app
    const { componentId, payload: { slotName, meta } } = e.data;
    client.pinApp({ componentId, slotName, ...meta });
  }
  if (e.data?.type === 'spark:action') {
    // micro-app emitted a domain action (e.g. "open_deal", "schedule_meeting")
    handleDomainAction(e.data.payload);
  }
});
```

| Event | Direction | When |
|---|---|---|
| `spark:ready` | iframe → host | Component mounted, includes render timing |
| `spark:pinned` | iframe → host | User pinned via `window.spark.pin()` |
| `spark:action` | iframe → host | Domain action emitted via `window.spark.action()` |
| `spark:error` | iframe → host | Runtime error inside iframe |
| `spark:data_applied` | iframe → host | Data Bridge swap completed |
| `spark:pong` | iframe → host | Response to host `spark:ping` |

Send commands inbound with `iframeEl.contentWindow.postMessage({ type: 'spark:data', data: {...} }, '*')`.

### Data Bridge

Swap sample data for real data without regenerating the component:

```bash
curl -X POST http://localhost:8000/api/components/{id}/data/swap \
  -H "X-Tenant-ID: acme-corp" \
  -d '{"real_data": { "pipeline_value": 4200000, "deals": [...] }}'
```

The component re-renders with live data. Cached in Redis per tenant — no LLM call required.

### Python Data Transform Layer (new in v3.4.0)

Can't pre-aggregate your data? Describe the computation in plain English — Spark generates safe Python, executes it in the [Monty](https://github.com/pydantic/monty) sandbox (no I/O, no network, microseconds), and stores the result in the Data Bridge.

```bash
# Transform raw orders into a revenue summary — then cache it for the component
curl -X POST http://localhost:8000/api/components/{id}/data/transform \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data": { "orders": [...10k rows...] },
    "transform": "Top 5 products by revenue this month",
    "ttl_seconds": 3600
  }'
# → { "status": "ok", "output_keys": ["top_products"], "execution_ms": 0.8, "cached": true }
```

Or preview without caching (great for the Playground):

```bash
curl -X POST http://localhost:8000/api/transform/preview \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data": { "orders": [...] },
    "transform": "Total revenue by category, sorted highest first"
  }'
# → { "code": "...", "result": { "by_category": [...] }, "execution_ms": 0.4 }
```

SDK shorthand:

```typescript
// Transform + cache for a component
await spark.transformData(componentId, rawData, "Top 5 products by revenue");

// Preview only — get the generated code + output back
const { code, result } = await spark.previewTransform(rawData, "Sum by category");
```

---

## API Reference

### A2A — Generation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/a2a/generate` | Generate micro-app from prompt |
| GET | `/api/a2a/render?prompt=` | Magic link — returns iframe HTML directly |

**Generate request:**

```json
{
  "prompt": "Build a sales pipeline dashboard",
  "data_context": { "pipeline_value": 4200000 },
  "component_id": "abc-123",
  "llm_config": {
    "provider": "openrouter",
    "model": "anthropic/claude-3.5-sonnet",
    "api_key": "sk-or-..."
  }
}
```

**Generate response:**

```json
{
  "component_id": "a3f7b2e1-...",
  "iframe_url":   "http://localhost:8000/api/components/a3f7b2e1-.../iframe",
  "status":       "compiled",
  "name":         "SalesPipelineDashboard",
  "bundle_size_bytes": 18432,
  "cache_hit":    false,
  "reasoning":    "..."
}
```

### Pinned Apps

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/apps` | List all pinned apps for the current user |
| POST | `/api/apps/pin` | Pin a component to a named slot |
| GET | `/api/apps/{pin_id}` | Get a single pinned app |
| PATCH | `/api/apps/{pin_id}` | Update pin metadata (description, icon, sort_order) |
| POST | `/api/apps/{pin_id}/regenerate` | Regenerate the component under this pin |
| DELETE | `/api/apps/{pin_id}` | Unpin |

**Pin request:**

```json
{
  "component_id": "a3f7b2e1-...",
  "slot_name":    "pipeline",
  "description":  "Q1 Sales Pipeline",
  "icon":         "📊",
  "sort_order":   1
}
```

**Regenerate request** (optional — omit to reuse the original prompt):

```json
{
  "prompt": "Add a stage conversion funnel and highlight at-risk deals in red",
  "data_context": { "pipeline_value": 4200000 }
}
```

**Regenerate response:**

```json
{
  "id":                    "pin-9x2k-abc",
  "previous_component_id": "a3f7b2e1-...",
  "new_component_id":      "c8d4e5f6-...",
  "iframe_url":            "http://localhost:8000/api/components/c8d4e5f6-.../iframe"
}
```

### Components

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/components` | List compiled components |
| GET | `/api/components/{id}` | Get component metadata |
| GET | `/api/components/{id}/iframe` | Serve sandboxed iframe HTML |
| POST | `/api/components/{id}/data` | Data endpoint called by iframe at runtime |
| POST | `/api/components/{id}/data/swap` | Data Bridge — store real data in Redis |
| PATCH | `/api/components/{id}/data` | Merge partial data into existing Data Bridge entry |

### Python Data Transform

| Method | Endpoint | Scope | Description |
|---|---|---|---|
| POST | `/api/components/{id}/data/transform` | generate | LLM → Python → Monty → cache in Data Bridge |
| POST | `/api/transform/preview` | generate | Transform without caching (Playground / debug) |
| GET | `/api/components/{id}/data/transform/code` | read | Return the last generated Python code for a component |

**Transform request:**

```json
{
  "raw_data": { "orders": [...] },
  "transform": "Top 5 products by revenue this month",
  "ttl_seconds": 3600,
  "dry_run": false
}
```

**Transform response:**

```json
{
  "status": "ok",
  "output_keys": ["top_products"],
  "execution_ms": 0.8,
  "cached": true,
  "component_id": "a3f7b2e1-...",
  "ttl_seconds": 3600
}
```

### Chat (Studio mode)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat/message` | Non-streaming — send prompt, get response |
| POST | `/api/chat/message/stream` | SSE stream — progress + done events |

Pass `component_id` in the request body to iterate on an existing micro-app (bolt.new-style).

### Dashboards

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboards/layout` | Get saved grid layout for a dashboard |
| PUT | `/api/dashboards/layout` | Save grid layout |

### Auth

**API keys** are the recommended auth method (v3.4.0+):

```bash
# Create a key (requires admin scope or dev mode)
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"label": "My App", "scopes": ["generate", "read"]}'
# → { "key": "sk_live_...", "id": "...", "scopes": [...] }
# The raw key is shown ONCE — store it.

# Use the key on all subsequent requests
curl http://localhost:8000/api/components \
  -H "Authorization: Bearer sk_live_..."
```

Legacy options (still supported):

```
X-Tenant-ID: acme-corp
X-User-ID:   user-42
```

Or a compact Bearer token:

```
Authorization: Bearer <base64(tenantId:userId)>
```

**Scopes:** `generate` · `read` · `pin` · `admin` — API keys carry a scope list; each route enforces the minimum required scope.

### API Keys

| Method | Endpoint | Scope | Description |
|---|---|---|---|
| POST | `/api/keys` | admin | Create a new API key |
| GET | `/api/keys` | admin | List all active keys (prefix only, never full key) |
| DELETE | `/api/keys/{id}` | admin | Revoke a key |

---

## TypeScript SDK

```bash
npm install @spark-engine/sdk
```

### SparkClient

```typescript
import { SparkClient } from '@spark-engine/sdk';

const client = new SparkClient({
  baseUrl:  'https://spark.yourdomain.com',
  tenantId: 'acme-corp',
  userId:   'user-42',
});

// Generate
const result = await client.generate({
  prompt: 'Build a sales pipeline dashboard',
  dataContext: { pipeline_value: 4200000 },
});

// Pin
const pin = await client.pinApp({
  componentId: result.componentId,
  slotName:    'pipeline',
  icon:        '📊',
});

// Regenerate — pin.id stays the same, component underneath is swapped
const updated = await client.regeneratePin(pin.id, {
  prompt: 'Add a conversion funnel',
});

// Push live data (Data Bridge — no regeneration)
await client.pushData(result.componentId, { pipeline_value: 5100000 });
```

### SparkWidget

Zero styling. Drop it anywhere:

```tsx
import { SparkWidget } from '@spark-engine/sdk';
import type { SparkWidgetHandle } from '@spark-engine/sdk';
import { useRef } from 'react';

function ChatMessage({ componentId }: { componentId: string }) {
  const widgetRef = useRef<SparkWidgetHandle>(null);

  return (
    <SparkWidget
      ref={widgetRef}
      iframeUrl={client.iframeUrl(componentId)}
      iframeStyle={{ width: '100%', height: 480, border: 'none', borderRadius: 12 }}
      onReady={({ renderMs }) => console.log(`Rendered in ${renderMs}ms`)}
      onPinned={({ slotName, meta }) => client.pinApp({ componentId, slotName })}
      onAction={({ type, data }) => handleDomainAction(type, data)}
    />
  );
}
```

**Imperative API (via ref):**

```typescript
widgetRef.current?.sendData({ pipeline_value: 5100000 });  // Data Bridge
widgetRef.current?.ping();                                  // Health check
```

### useSpark hook

```tsx
import { useSpark } from '@spark-engine/sdk';

function AgentChat() {
  const { status, error, pinnedApps, generate, pin, regenerate, unpin } = useSpark(client);

  const handleUserMessage = async (message: string) => {
    const result = await generate({ prompt: message });
    // result.componentId is ready to pass to SparkWidget
  };

  return (
    <div>
      <SparkNavBar
        pinnedApps={pinnedApps}
        onUnpin={(pinId) => unpin(pinId)}
        direction="horizontal"
      />
      {/* ... render SparkWidgets for each message */}
    </div>
  );
}
```

### SparkNavBar

Unstyled reference nav bar. Fork it, don't depend on it:

```tsx
import { SparkNavBar } from '@spark-engine/sdk';

<SparkNavBar
  pinnedApps={pinnedApps}
  onSelect={(pin) => setActivePinId(pin.id)}
  onUnpin={(pinId) => client.unpinApp(pinId)}
  direction="horizontal"
  renderItem={({ pin, isActive, onSelect, onUnpin }) => (
    <MyNavItem
      icon={pin.icon}
      label={pin.description || pin.slot_name}
      active={isActive}
      onClick={onSelect}
      onUnpin={onUnpin}
    />
  )}
/>
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                         │
│                                                             │
│  ┌────────────┐   ┌─────────────┐   ┌────────────────────┐  │
│  │ Chat Shell │   │  Nav Bar    │   │ Dashboard (grid)   │  │
│  └─────┬──────┘   └──────┬──────┘   └─────────┬──────────┘  │
│        │                 │                    │              │
│        └─────────────────┴────────────────────┘              │
│                          │                                   │
│               @spark-engine/sdk                              │
│          SparkClient  ·  SparkWidget  ·  useSpark            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP + Bearer token
           ┌───────────────▼─────────────────────────┐
           │               Spark API                 │
           │                                         │
           │  /api/a2a/*        /api/apps/*           │
           │  /api/components/* /api/chat/*           │
           │  /api/dashboards/*                       │
           │                                         │
           │  ┌────────────┐    ┌──────────────────┐  │
           │  │ LLM Gateway│    │ Compiler         │  │
           │  │ OpenAI /   │    │ (esbuild+Solid)  │  │
           │  │ OpenRouter /│   └──────────────────┘  │
           │  │ LiteLLM /  │    ┌──────────────────┐  │
           │  │ LLMGW      │    │ Validator        │  │
           │  └────────────┘    │ (AST scan)       │  │
           │                    └──────────────────┘  │
           │  ┌────────────┐    ┌──────────────────┐  │
           │  │ PostgreSQL │    │ Redis            │  │
           │  │ components │    │ Data Bridge      │  │
           │  │ pinned_apps│    │ cache            │  │
           │  └────────────┘    └──────────────────┘  │
           └───────────────┬─────────────────────────┘
                           │
           ┌───────────────▼─────────────────────────┐
           │          Sandboxed iframe               │
           │                                         │
           │  window.__SPARK  ·  window.spark.*       │
           │  spark:ready  spark:pinned  spark:action │
           └─────────────────────────────────────────┘
```

---

## LLM Gateway

All providers speak the OpenAI `/v1/chat/completions` format. Configure via env or per-request `llm_config`.

| Provider | `base_url` | Env key |
|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `litellm` | `http://localhost:4000/v1` | `LITELLM_API_KEY` |
| `llmgw` | set via `LLMGW_BASE_URL` | `LLMGW_API_KEY` |
| `custom` | set via config | `CUSTOM_LLM_API_KEY` |

Set `LLM_FALLBACK_PROVIDER` + `LLM_FALLBACK_MODEL` for automatic failover.

---

## Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker + Docker Compose

### Environment

```bash
cp .env.example .env
```

Minimum required:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/spark
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
```

Full options in [.env.example](.env.example).

### Local development

```bash
# Start postgres + redis
docker-compose up -d postgres redis

# Backend
cd backend
pip install -r requirements.txt
DATABASE_MODE=postgres uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

Or run everything via Docker:

```bash
docker-compose up --build
```

### Migrations

`database/migrations/` is mounted as `docker-entrypoint-initdb.d` — migrations run automatically **only when the Postgres data volume is first created**. If you already had a volume from an older checkout, new SQL files are **not** re-run; apply them manually:

```bash
# From host (compose example)
docker compose exec -T postgres psql -U postgres -d spark -f /docker-entrypoint-initdb.d/20260322120000_dashboard_layouts.sql

# Or with DATABASE_URL
psql $DATABASE_URL -f database/migrations/20260322000000_add_pinned_apps.sql
psql $DATABASE_URL -f database/migrations/20260322120000_dashboard_layouts.sql
```

---

## Component Templates

9 pre-built templates for fast generation without cold-start latency:

| Template | Category | Description |
|---|---|---|
| `StatCard` | card | KPI metric card with trend indicator |
| `DataTable` | table | Filterable, sortable table with search |
| `LineChart` | chart | Time-series line chart |
| `BarChart` | chart | Categorical bar chart |
| `DonutChart` | chart | Donut / pie with legend |
| `HeatmapChart` | chart | Activity heatmap (GitHub-style) |
| `MixedChart` | chart | Bar + line combo |
| `ListWithSearch` | list | Searchable entity list |
| `MetricsDashboard` | dashboard | Multi-KPI dashboard |

---

## Security

- **AST validation**: Generated code is scanned before compilation. Forbidden APIs (`window`, `fetch`, `eval`, `XMLHttpRequest`, `document.cookie`) are rejected.
- **Sandboxed execution**: Components run in `<iframe sandbox="allow-scripts allow-same-origin">`.
- **Multi-tenant isolation**: PostgreSQL RLS policies scope all queries to `(tenant_id, user_id)`.
- **Auth**: Plug in your own JWT verification middleware. The `X-Tenant-ID` / `X-User-ID` values are trusted after verification.

---

## Documentation

- [CHANGELOG](CHANGELOG.md)
- [Data Bridge Pattern](docs/DATA_BRIDGE.md)
- [Content-Addressable Generation (CAG)](docs/CAG.md)
- [Integration Guide](docs/INTEGRATION.md)

---

## License

**Dual license**

- **AGPLv3**: Free for open-source use. If you run Spark as a service and integrate with your application, you must open-source your connecting application.
- **Commercial**: Contact [enterprise@spark.ai](mailto:enterprise@spark.ai) for proprietary / SaaS use.
