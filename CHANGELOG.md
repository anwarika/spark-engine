# Changelog

All notable changes to Spark will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-02-28

### ⚠️ BREAKING CHANGES

- **Generated apps**: Solid.js + ApexCharts → React + shadcn/ui + Recharts
- **LLM**: llm_providers.py deprecated; use LLMGateway (llm_gateway.py)
- **Chat UI**: DaisyUI → shadcn/ui
- **Data Bridge**: createResource/window.__DATA_MODE → postMessage `spark_data` with `data` prop
- **Cache**: CAG keys now include `engine:react`; Solid.js outputs are not reused

### Added

- **LLM Gateway**: Pluggable provider abstraction
  - Supports: openai, openrouter, litellm, llmgw, custom
  - Single config: LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, LLM_BASE_URL
  - Fallback provider support
  - Per-request override via A2A `llm_config`
- **React + shadcn/ui**: Generated components use React 18, shadcn, Recharts, Lucide
- **9 React templates**: StatCard, DataTable, LineChart, BarChart, PieChart, AreaChart, ComposedChart, ListWithSearch, MetricsDashboard
- **shadcn-ui-bundle.js**: Minimal shadcn stub for iframe component rendering
- **A2A API extensions**: template_hint, theme, llm_config; response: render_url, iframe_url, embed_html, metadata
- **docs/LLM_GATEWAY.md**: LLM configuration guide
- **docs/MIGRATION_V3.md**: v2.x → v3.0 migration guide

### Changed

- Compiler uses esbuild with React JSX; externals for react, react-dom, recharts, @/components/ui/*, lucide-react
- Validator allowlist updated for React imports; forbidden: window, document, fetch, eval, etc.
- Iframe HTML: React/Recharts CDN, shadcn bundle, spark_data/spark_theme postMessage handlers
- Frontend: App, ChatWindow, MessageBubble, ComponentsView, MicroappIframe use shadcn
- Docker: compiler npm deps instead of global solid-js

### Fixed

- CAG hash includes engine identifier for React vs Solid.js cache separation

## [Unreleased]

### Added

- **Content-Addressable Generation (CAG)**: Intelligent component deduplication system
  - Automatically detects when users request similar/identical components
  - Returns existing components instantly without LLM regeneration (~1500ms saved)
  - Saves $0.001-0.003 per CAG hit by avoiding LLM API calls
  - Content hashing based on normalized prompt + template + data profile
  - `GET /api/components/search?content_hash=...` endpoint for CAG lookups
  - `GET /api/cag/metrics` endpoint for monitoring hit rates and performance
  - Reuse count tracking in `generation_metadata` field
  - Database migration adds: `content_hash`, `prompt_normalized`, `generation_metadata` columns

- **CAG Documentation**: Comprehensive guide at `docs/CAG.md` with:
  - Architecture diagrams
  - Normalization rules and synonym groups
  - Performance benchmarks
  - Debugging guides
  - Best practices

### Changed

- **Chat endpoints** now check for existing components before LLM generation
- **Component creation** now stores content fingerprints for future CAG lookups
- **Metrics logging** enhanced with CAG hit/miss events and timing breakdown
- **Cache strategy** labels updated to reflect CAG status (e.g., `cag_miss_llm_generated`)

### Performance

- **CAG HIT response time**: ~85ms (vs ~2500ms for fresh generation)
- **CAG lookup overhead**: +10-20ms when no match found (negligible)
- **Hit rate**: Varies by usage patterns (typically 20-40% in multi-user environments)

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

### Fixed

- **Numeric precision**: Mock data generator now properly rounds all numeric values to 2 decimal places (currency) or 4 decimal places (rates/percentages)
- **Python f-string escaping**: Fixed JavaScript literal braces within iframe HTML f-strings

### Documentation

- Added `docs/MIGRATION_V2.md` - Comprehensive upgrade guide from v1.x
- Added `docs/DATA_BRIDGE.md` - Technical deep-dive on data bridge pattern
- Added `CHANGELOG.md` - Following Keep a Changelog format
- Added GitHub issue/PR templates (`.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`)
- Updated README with version badges, documentation links, and expanded contributing section

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
