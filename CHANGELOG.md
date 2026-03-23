# Changelog

All notable changes to Spark will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.3.0] - 2026-03-22

This release makes Spark **headless and API-first**. The backend now speaks a clean protocol — any chat application can embed Spark without coupling to the default frontend. A TypeScript SDK ships alongside the new pinned apps API.

### Added

#### Headless API — Pinned Apps (`/api/apps`)

- **`GET /api/apps`** — List all pinned apps for the current user (tenant + user scoped)
- **`POST /api/apps/pin`** — Pin a component to a named slot (`slot_name`); slot identity is stable even when the component underneath is regenerated
- **`GET /api/apps/{pin_id}`** — Fetch a single pinned app with enriched `iframe_url`
- **`PATCH /api/apps/{pin_id}`** — Update pin metadata: `description`, `icon`, `sort_order`, `metadata`
- **`POST /api/apps/{pin_id}/regenerate`** — Atomically swap the component under a pin; accepts an optional new `prompt` + `data_context`, otherwise reuses the original prompt. Returns `previous_component_id` + `new_component_id`; `pin_id` is unchanged
- **`DELETE /api/apps/{pin_id}`** — Unpin

- **`pinned_apps` table** (`database/migrations/20260322000000_add_pinned_apps.sql`) — `(tenant_id, user_id, slot_name)` unique constraint, `component_id` FK with `ON DELETE RESTRICT`, RLS policies, sorted indexes
- **`PinnedApp`, `PinAppRequest`, `UpdatePinMetaRequest`, `UpdatePinComponentRequest`, `RegenerateResponse`** — Pydantic response + request models

#### Auth Upgrade

- **Bearer token support** (`Authorization: Bearer <base64(tenantId:userId)>`) — compact, integrator-friendly alternative to `X-Tenant-ID` / `X-User-ID` headers
- `_parse_bearer()` in `backend/app/middleware/auth.py` decodes and validates; graceful fallback to header auth
- Integrators mint tokens on their backend: `btoa(tenantId + ':' + userId)`

#### `spark:*` Event Protocol (iframe ↔ host)

Full structured postMessage protocol replacing ad-hoc globals:

- `window.__SPARK` config object replaces individual `window.__COMPONENT_*` globals
- **Outbound** (iframe → host): `spark:ready` (with render timing), `spark:error`, `spark:pinned`, `spark:action`, `spark:data_applied`, `spark:pong`
- **Inbound** (host → iframe): `spark:data` / `data_swap` (back-compat), `spark:ping`, `spark:set_theme`
- `window.spark.emit(name, payload)` — outbound bus accessible inside component code
- `window.spark.pin(slotName, meta)` — convenience method to trigger `spark:pinned`
- `window.spark.action(type, data)` — convenience method to trigger `spark:action`
- `window.sendToParent` alias preserved for back-compat

#### `@spark-engine/sdk` TypeScript Package (`packages/spark-sdk`)

- **`SparkClient`** — typed HTTP client; Bearer token construction; `generate`, `listComponents`, `getComponent`, `iframeUrl`, `listPinnedApps`, `pinApp`, `getPinnedApp`, `updatePinMeta`, `regeneratePin`, `unpinApp`, `pushData`
- **`SparkWidget`** — headless React component (`forwardRef`); props: `iframeUrl`, styling, event callbacks (`onReady`, `onError`, `onPinned`, `onAction`, `onDataApplied`, `onEvent`); imperative handle: `sendData(data, mode)`, `ping()`, `send(cmd)`, `iframe` ref
- **`useSpark`** hook — full lifecycle state: `{ status, error, lastGenerated, pinnedApps, generate, pin, updatePin, regenerate, unpin, refreshPinnedApps, clearError }`; optimistic UI updates for pin/unpin/regenerate
- **`SparkNavBar`** — unstyled reference nav component; `direction` prop (`horizontal` / `vertical`); `renderItem` prop for custom rendering
- Full TypeScript interfaces: `SparkClientConfig`, `SparkComponent`, `GenerateRequest/Response`, `PinnedApp`, `RegenerateRequest/Response`, `SparkEvent<T>`, `SparkCommand`, `AnySparkEvent`
- `SparkError` class with `status` + `detail`
- Passes `tsc --noEmit` with zero errors (React 18 peer deps)

#### Storage Layer

- **`PostgresStorage`** — full implementation of 6 new pinned-app abstract methods: `create_pinned_app`, `get_pinned_app`, `list_pinned_apps`, `update_pinned_app_component`, `update_pinned_app_meta`, `delete_pinned_app`
- **`SupabaseStorage`** — same 6 methods implemented, plus missing `find_component_by_content_hash` (fixes crash in cloud deployments)
- Both implementations maintain full parity — local Docker (postgres mode) and cloud (Supabase mode) are functionally equivalent

#### Frontend (`frontend/src`)

- `appsAPI` service (`listPinnedApps`, `pinApp`, `getPinnedApp`, `updatePinMeta`, `regeneratePin`, `unpinApp`)
- `normalizePinnedApp()` — handles both Supabase nested-join format and Postgres flat format
- `dashboardsAPI` service (`getLayout`, `saveLayout`)
- New TypeScript types: `PinnedApp`, `PinAppRequestBody`, `UpdatePinMetaRequestBody`, `RegeneratePinRequestBody`, `RegeneratePinResponse`, `SparkPinnedPostMessage`, `DashboardLayoutItem`, `DashboardLayoutResponse`
- First-party pinned apps UI: nav strip, Pinned tab (regenerate / unpin / iterate)
- Dashboard canvas — `react-grid-layout` view with server-persisted layout

### Changed

- `README.md` — complete rewrite: headless positioning, 7 demo screenshots (pipeline, account intelligence, meeting prep, incident command, sprint health, personal budget, API walkthrough), full API reference including `/api/apps`, SDK docs, architecture diagram
- Version badge updated to 3.3.0

### Fixed

- `RuntimeError: Directory 'static/assets' does not exist` on startup — `backend/static/assets/` directory now created on first run
- `Can't instantiate abstract class SupabaseStorage` — missing `find_component_by_content_hash` method added to `SupabaseStorage`

## [3.2.0] - 2026-03-01

### Added

- **Studio Mode iteration** — Multi-turn microapp editing (bolt.new-style)
  - "Iterate" button on each microapp opens full-screen split-panel studio
  - Left: live iframe preview; right: scoped iteration chat
  - Each edit creates a new component with `parent_component_id` lineage
  - Revert/undo: "↩ Revert" button in header and per-message revert links
- **ChatMessage.component_id** — Request body field to iterate on an existing component
- **A2AGenerateRequest.component_id** — A2A callers can pass component ID to edit instead of create
- **Hallucination mitigation** (5-layer defence):
  1. Data schema injected into every edit prompt
  2. temperature=0.15 for edit generation (deterministic)
  3. Fields already used in existing code anchored as safe hints
  4. Auto-retry (up to 2 attempts) with validation/compile error fed back
  5. CodeValidator schema field contract — rejects hallucinated `apiData().X` fields before iframe renders
- **LLMService.generate_edit_response()** — Edit-focused system prompt with modern layout guidance

### Changed

- Iteration chat response shows description only (reasoning) instead of raw code
- `microapp_ready` SSE event gains `parent_component_id` for in-place iframe updates
- Studio loading UI matches main chat step-by-step badge tracker

## [3.1.0] - 2026-03-01

### Added

- **LLM Gateway abstraction layer** (`backend/app/services/llm_gateway.py`)
  - Unified OpenAI-compatible client for `openai`, `openrouter`, `litellm`, `llmgw`, `custom` providers
  - Built-in fallback provider support
  - Per-request `LLMConfig` override via A2A endpoint
- New env vars: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLMGW_BASE_URL`, `LLMGW_API_KEY`, `LITELLM_API_KEY`, `LLM_FALLBACK_*` family

### Changed

- `A2AGenerateRequest.provider_config` (Dict) → `llm_config` (LLMConfig) — structured per-request override
- LLMService now uses async `AsyncOpenAI` client for all providers

### Removed

- `llm_providers.py` (OpenAIProvider / AnthropicProvider / OpenRouterProvider) — replaced by LLMGateway

### Breaking Changes

- A2A API: `provider_config` field renamed to `llm_config`; type changed from Dict to `LLMConfig` schema

## [2.0.0] - 2026-02-10

### ⚠️ BREAKING CHANGES

This release replaces Chart.js with ApexCharts and introduces the Data Bridge pattern. Components generated with v1.x may need regeneration.

### Added

- **ApexCharts Integration**: Modern charting library with smooth animations, gradients, and interactive tooltips
  - Added ApexCharts v3.54.1 to iframe importmap
  - Replaced Chart.js with ApexCharts across all chart templates
  - Added 6 ApexCharts config primitives: `apexLineConfig`, `apexBarConfig`, `apexAreaConfig`, `apexDonutConfig`, `apexSparklineConfig`, `apexMixedConfig`

- **New Chart Templates** (3 new templates):
  - `DonutChart` - Category breakdown with legends
  - `HeatmapChart` - Time-series intensity visualization
  - `MixedChart` - Combined line + bar charts for dual-axis comparisons

- **Data Bridge Pattern**: Sample → real data swapping
  - Added `window.__DATA_MODE` flag for toggling between `'sample'` and `'real'` modes
  - Added Solid.js `DataContext` provider in iframe for reactive data management
  - Created `/api/components/{id}/data/swap` POST endpoint to store real data
  - Updated `/api/components/{id}/data` to support `data_mode: "real" | "sample"` parameter
  - Components now use reactive `createResource` sources that refetch when mode changes
  
- **Data Bridge Primitives** (4 new):
  - `DATA_CONTEXT_SETUP` - Solid.js context provider boilerplate
  - `DATA_VALIDATOR` - Runtime schema validation
  - `DATA_TRANSFORMER` - Data format/normalization utilities
  - `USE_DATA_BRIDGE` - Hook for consuming data context

- **Data Validation**: Pydantic models for data schemas
  - `DataSwapRequest` - POST body validation for `/data/swap`
  - `DataBridgePayload` - Data bridge envelope structure
  - `validate_data_shape()` - Validate data contains expected keys

- **Frontend Enhancements**:
  - Added Sample/Real data mode toggle to `MicroappIframe` component
  - Added data mode indicator badge
  - Implemented postMessage-based mode switching
  - iframe uses `useRef` for direct contentWindow access

### Changed

- **Chart Templates**: All chart templates now use ApexCharts API
  - `LineChart` - Smooth curves, gradients, hover tooltips
  - `BarChart` - Rounded corners, columnWidth control
  - `MetricsDashboard` - Area chart with gradient fill

- **Template Fetch Pattern**: All 9 templates now:
  - Pass `data_mode` in fetch body for bridge support
  - Use reactive `createResource` source: `() => window.__DATA_MODE`
  - Automatically refetch when data mode changes

- **LLM System Prompt**: 
  - Replaced Chart.js documentation with ApexCharts examples
  - Added data bridge usage patterns
  - Updated available templates list (9 templates)
  - Added `data_mode` to fetch body examples

- **Compiler Configuration**:
  - Updated `external` dependencies: removed `chart.js`, added `apexcharts`
  - Updated package.json: `apexcharts@^3.54.1`

### Removed

- **Chart.js**: Removed from all templates, iframe HTML, and compiler externals
- **Chart.js Primitives**: Removed old `CHART_LINE_CONFIG`, `CHART_BAR_CONFIG`, `CHART_PIE_CONFIG` (replaced with ApexCharts equivalents)

### Migration Guide

See [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md) for detailed upgrade instructions.

**Quick Migration:**

1. **No action needed** if using the chat interface - new components will use ApexCharts automatically
2. **Regenerate existing components** if you want ApexCharts styling
3. **Update custom code** that imports `chart.js` to use `apexcharts` instead

**Data Bridge Usage:**

```javascript
// Store real data (from your backend/API)
await fetch('/api/components/{id}/data/swap', {
  method: 'POST',
  body: JSON.stringify({ 
    mode: 'real', 
    data: { revenue: [...], metrics: [...] } 
  })
});

// Trigger swap (via UI toggle or programmatically)
iframeWindow.postMessage({ type: 'data_swap', mode: 'real' }, '*');
```

### Technical Details

**Bundle Sizes:**
- ApexCharts CDN: ~45KB gzipped (cached by browser)
- Template bundles: 10-15KB (unchanged from v1.x)
- Total overhead: +45KB on first load, 0KB on subsequent loads

**API Compatibility:**
- All v1.x endpoints remain functional
- New `/data/swap` endpoint is additive
- `/data` endpoint accepts optional `data_mode` parameter (backward compatible)

**Performance:**
- Chart render time: <300ms (improved from Chart.js's ~400ms)
- Data swap latency: <100ms
- Total time to interactive: maintained at <2s

## [1.0.0] - 2025-11-23

### Added
- Initial release of Spark
- Solid.js component generation with LLM
- Chart.js integration for visualizations
- 6 pre-built templates
- Multi-tenant architecture with PostgreSQL RLS
- Redis caching for compiled bundles
- A2A (Agent-to-Agent) protocol support
- React + DaisyUI frontend
- Docker Compose setup for local development
