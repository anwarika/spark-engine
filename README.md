# Spark

### A2A Micro App Generation Service

Generate Solid.js micro-apps from natural language. Connect your AI agent—Spark handles generation, validation, compilation, and serving.

[![Version](https://img.shields.io/badge/version-3.2.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-AGPLv3-green.svg)](LICENSE)

---

## What is Spark?

Spark is an **Agent-to-Agent (A2A)** service that turns prompts into renderable UI. Your AI agent sends a request with a prompt and optional data—Spark returns a compiled micro-app URL.

- **Pluggable LLM Gateway**: OpenAI, OpenRouter, LiteLLM, Bloomberg LLMGW, or any OpenAI-compatible endpoint
- **Per-request config**: Override provider, model, and API credentials per request
- **Built-in fallback**: Automatic failover to a backup provider on errors

## Get Started

### Quick Start

```bash
git clone https://github.com/your-org/spark.git
cd spark
export OPENAI_API_KEY=sk-...
docker-compose up -d
```

### Use It in Your Agent

**Magic Link** — Have your bot send this to the user:
```
http://localhost:8000/api/a2a/render?prompt=Show+me+sales+for+2024
```

**API Call** — For programmatic access:

```bash
curl -X POST http://localhost:8000/api/a2a/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a dashboard for these metrics",
    "data_context": { "revenue": 5000, "growth": "15%" }
  }'
```

**Iterate on existing component** — Pass `component_id` to edit instead of create:

```bash
curl -X POST http://localhost:8000/api/a2a/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Add a KPI card for total revenue",
    "component_id": "abc-123-existing-component-uuid"
  }'
```

**Per-request LLM override** — Use a different provider/model per request:

```bash
curl -X POST http://localhost:8000/api/a2a/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Build a revenue chart",
    "llm_config": {
      "provider": "openrouter",
      "model": "anthropic/claude-3.5-sonnet",
      "api_key": "sk-or-..."
    }
  }'
```

## LLM Gateway

All providers speak the OpenAI `/v1/chat/completions` format. Configure via env or per-request `llm_config`.

| Provider   | base_url                         | Env Key           |
|-----------|-----------------------------------|-------------------|
| openai    | https://api.openai.com/v1         | OPENAI_API_KEY    |
| openrouter| https://openrouter.ai/api/v1      | OPENROUTER_API_KEY|
| litellm   | http://localhost:4000/v1          | LITELLM_API_KEY   |
| llmgw     | (set via LLMGW_BASE_URL)         | LLMGW_API_KEY     |
| custom    | (set via config)                 | CUSTOM_LLM_API_KEY|

**Fallback**: Set `LLM_FALLBACK_PROVIDER`, `LLM_FALLBACK_MODEL`, etc. to fail over on errors.

See [.env.example](.env.example) for the full config.

## Features

- **Generative UI**: LLM produces Solid.js components—dashboards, charts, tables, KPIs
- **9 Pre-built Templates**: StatCard, DataTable, LineChart, BarChart, DonutChart, HeatmapChart, MixedChart, ListWithSearch, MetricsDashboard
- **Studio Mode iteration**: Multi-turn microapp editing (bolt.new-style)—click "Iterate" on any microapp to open a split-panel studio with live preview and scoped chat; revert/undo support
- **Data Bridge**: Sample → real data swap without regeneration
- **CAG**: Content-addressable generation for deduplication
- **Security**: AST validation, forbidden API detection, sandboxed iframe execution
- **Multi-tenant**: PostgreSQL RLS isolation

## Architecture

```
┌─────────────────┐
│ External Agent  │
└────────┬────────┘
         │ POST /api/a2a/generate
         ▼
┌─────────────────┐     ┌──────────────┐
│  A2A Router      │────▶│ LLM Gateway  │──▶ OpenAI / OpenRouter / LiteLLM / custom
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Validator      │     │  Compiler    │
│  Compiler       │     │  (esbuild)   │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│ PostgreSQL      │  Redis (cache)
└─────────────────┘
```

## API Endpoints

### A2A

| Method | Endpoint               | Description                          |
|--------|------------------------|--------------------------------------|
| POST   | /api/a2a/generate      | Generate micro-app from prompt       |
| GET    | /api/a2a/render?prompt=| Magic link: returns HTML + iframe     |

### Components

| Method | Endpoint                         | Description                 |
|--------|----------------------------------|-----------------------------|
| GET    | /api/components                  | List components             |
| GET    | /api/components/{id}/iframe     | Get iframe HTML            |
| POST   | /api/components/{id}/data        | Data endpoint for iframes  |
| POST   | /api/components/{id}/data/swap   | Store real data (Data Bridge) |

### Chat

| Method | Endpoint                  | Description                                      |
|--------|---------------------------|--------------------------------------------------|
| POST   | /api/chat/message         | Send message, get response (non-streaming)      |
| POST   | /api/chat/message/stream  | Send message, get SSE stream (progress + done)   |

Chat supports `component_id` in the request body to iterate on an existing microapp.

## Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL, Redis

### Environment

Copy `.env.example` and set at minimum:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/spark
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
```

See [.env.example](.env.example) for LLM Gateway options.

### Local Development

```bash
docker-compose up --build
# Or manual: backend with uvicorn, frontend with npm run dev
```

## Security

- **Code validation**: AST scan, forbidden APIs (`window`, `fetch`, `eval`, etc.)
- **Sandboxing**: Components run in iframe with `sandbox="allow-scripts allow-same-origin"`
- **Auth headers**: `X-Tenant-ID`, `X-User-ID` (placeholder—integrate with your auth)

## Documentation

- [CHANGELOG](CHANGELOG.md)
- [Data Bridge Pattern](docs/DATA_BRIDGE.md)
- [Content-Addressable Generation (CAG)](docs/CAG.md)
- [Integration Guide](docs/INTEGRATION.md)

## License

**Dual license**

- **AGPLv3**: Use in open-source projects. If you run Spark as a service and integrate with your app, you must open-source your connecting application.
- **Commercial**: Contact [enterprise@spark.ai](mailto:enterprise@spark.ai) for proprietary use.
