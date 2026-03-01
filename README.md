<div align="center">

# Spark

### Generate UI with a single prompt

The open-source AI-powered micro-app generator. Describe a component, chart, or dashboard—Spark builds, compiles, and sandboxes it instantly.

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-AGPLv3-green.svg)](LICENSE)

**Docs** · [CHANGELOG](CHANGELOG.md)

</div>

---

> **Spark v3.0 is here!** React + shadcn/ui + Recharts for generated apps, pluggable LLM gateway, per-request config override. See [CHANGELOG.md](CHANGELOG.md).

---

## Table of Contents

- [What is Spark?](#what-is-spark)
- [Get Started](#get-started)
- [How It Works](#how-it-works)
- [What's Included](#whats-included)
- [How Spark Compares](#how-spark-compares)
- [Community](#community)
- [License](#license)

## What is Spark?

Spark is a standalone service that generates React + shadcn/ui micro-apps from natural language. Users interact via chat—the LLM decides whether to respond with text or generate a component. Generated code is compiled, validated, sandboxed, and served in an iframe.

**[Get started in 5 minutes →](#get-started)**

### What's Included

Spark is a fullstack solution for adding generative UI to your app. You get a React chat frontend plus a FastAPI backend that handles generation, compilation, and delivery.

**1. LLM-powered generation** — Pluggable gateway (OpenAI, OpenRouter, LiteLLM, Bloomberg LLMGW) generates React components on demand. Per-request model and temperature override.

**2. Instant compilation & caching** — esbuild compiles TSX in ~100–300ms. Content-Addressable Generation (CAG) deduplicates identical prompts—cache hits return in <200ms.

**3. Self-hosted** — Run the full stack on your infrastructure. Docker Compose for local dev; production-ready with PostgreSQL, Redis, and optional multi-tenant RLS.

## Get Started

```bash
git clone https://github.com/your-org/spark.git
cd spark
export OPENAI_API_KEY=sk-...
docker-compose up --build
# Open http://localhost:8000
```

**Option A: Magic Link (for agents)**

Have your bot send: `http://localhost:8000/api/a2a/render?prompt=Show+me+sales+for+2024`

**Option B: API call**

```bash
curl -X POST http://localhost:8000/api/a2a/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a dashboard for these metrics", "data_context": {"revenue": 5000, "growth": "15%"}}'
```

See [Integration Guide](docs/INTEGRATION.md) for LangChain, Vercel AI SDK, and OpenAI Actions.

**Documentation:** [LLM Gateway](docs/LLM_GATEWAY.md) · [Data Bridge](docs/DATA_BRIDGE.md) · [CAG](docs/CAG.md) · [Migration v2→v3](docs/MIGRATION_V3.md)

## How It Works

Register templates with the component library. The LLM selects one and streams props. Spark compiles, validates, and serves the result.

### 1. LLM generation

User sends a message. The LLM chooses a template (StatCard, DataTable, BarChart, etc.) and generates props.

```json
{
  "template": "BarChart",
  "props": { "data": [...], "title": "Monthly Revenue" }
}
```

### 2. Compilation & caching

esbuild compiles the template + props into React. CAG hashes the intent—identical prompts reuse cached bundles.

```bash
# Cache hit: ~200ms. Cache miss: ~2s P95
```

### 3. Sandboxed delivery

Compiled JS runs in an iframe with `sandbox="allow-scripts allow-same-origin"`. Data Bridge supports sample→real data swap via `postMessage`.

```ts
postMessage({ type: 'spark_data', mode: 'real', data: {...} });
```

## How Spark Compares

| Feature | Spark | Manual component builds | CopilotKit | Vercel AI SDK |
|---------|-------|-------------------------|------------|---------------|
| **Component selection** | AI picks template from library | You wire everything | Via LangGraph | Manual tool mapping |
| **Generated stack** | React + shadcn/ui + Recharts | Varies | Varies | SDK only |
| **Compilation** | esbuild, CAG cache | N/A | N/A | N/A |
| **Sandboxing** | iframe CSP | Manual | Manual | Manual |
| **Self-hostable** | Yes (AGPL) | N/A | Yes (MIT) | SDK only |
| **Best for** | AI-generated dashboards/charts | Full control | Multi-agent workflows | Streaming & tools |

## Community

Interested in contributing? Read the [Contributing Guide](docs/DEVELOPMENT.md).

Report bugs and feature requests via [GitHub Issues](https://github.com/your-org/spark/issues).

## License

Spark is available under a dual license:

- **AGPLv3** — Use freely in open-source or private experiments. If you run Spark as a service and integrate it with your app, you must open-source the connecting app under AGPL.
- **Commercial** — For proprietary use without open-sourcing. Contact [enterprise@spark.ai](mailto:enterprise@spark.ai) for a Commercial License.
