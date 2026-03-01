# Spark - AI-Powered Micro App Generation Service

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Spark is a standalone service that generates, validates, and serves dynamic React micro-apps through a chat interface. Users interact with an LLM that decides whether to respond with text or generate a React + shadcn/ui component. Generated components are compiled, validated, sandboxed, cached, and served to the frontend.

**🆕 What's New in v3.0:** React + shadcn/ui + Recharts for generated apps, pluggable LLM gateway (OpenAI/OpenRouter/LiteLLM/LLMGW), per-request LLM config override. See [CHANGELOG.md](CHANGELOG.md) for details.

## Developer Quickstart (5 Minutes)

Want to add "Generate UI" capabilities to your own AI agent or chat app?

1.  **Clone & Run**
    ```bash
    git clone https://github.com/your-org/spark.git
    cd spark
    # Set your LLM Key
    export OPENAI_API_KEY=sk-...  # or LLM_PROVIDER=openrouter + OPENROUTER_API_KEY
    # Run the embedded stack
    docker-compose -f docker-compose.embedded.yml up -d
    ```

2.  **Use it in your App**
    Spark is now running at `http://localhost:8000`.

    **Option A: Magic Link (Easiest)**
    Just have your bot send this link to the user:
    `http://localhost:8000/api/a2a/render?prompt=Show+me+sales+for+2024`

    **Option B: API Call (For Agents)**
    ```bash
    curl -X POST http://localhost:8000/api/a2a/generate \
      -H "Content-Type: application/json" \
      -d '{
        "prompt": "Create a dashboard for these metrics",
        "data_context": { "revenue": 5000, "growth": "15%" }
      }'
    ```

    See [Integration Guide](docs/INTEGRATION.md) for LangChain, Vercel AI SDK, and OpenAI Actions examples.

    **📖 Documentation:**
    - [LLM Gateway](docs/LLM_GATEWAY.md)
    - [Migration Guide v2.x → v3.0](docs/MIGRATION_V3.md)
    - [Data Bridge Pattern](docs/DATA_BRIDGE.md)
    - [Content-Addressable Generation (CAG)](docs/CAG.md)
    - [Changelog](CHANGELOG.md)

## Features

- **LLM-Powered Generation**: Pluggable LLM gateway (OpenAI, OpenRouter, LiteLLM, Bloomberg LLMGW) generates React components on demand
- **Content-Addressable Generation (CAG)**: Intelligent deduplication prevents regenerating identical components
- **Modern Charts**: Recharts integration for beautiful, interactive visualizations
- **Data Bridge**: Sample → real data swapping via postMessage (`spark_data`) for seamless data transitions
- **Multi-Layered Security**: AST analysis, forbidden API detection, and sandboxed execution
- **High Performance**: Redis caching, esbuild compilation, CAG reuse
- **Multi-Tenant Architecture**: Complete tenant isolation with PostgreSQL RLS
- **Chat Interface**: Clean React + shadcn/ui for natural interaction with data mode toggle
- **Component Registry**: Store, version, and manage generated components
- **9 Pre-Built Templates**: React + shadcn/ui templates for common visualization patterns

## Tech Stack

### Frontend
- React + TypeScript
- shadcn/ui + Tailwind CSS
- Zustand (state management)
- Axios (API client)

### Generated Micro Apps
- React + TypeScript
- shadcn/ui + Recharts for visualizations
- Lucide React icons
- Sandboxed iframe execution
- Data Bridge pattern (sample → real via `spark_data` postMessage)

### Backend
- FastAPI + Python 3.11+
- Pluggable LLM gateway (OpenAI, OpenRouter, LiteLLM, LLMGW)
- esbuild (React TSX compilation)
- PostgreSQL (Database)
- Redis (caching)

## Architecture

```
┌─────────────────┐
│  React Frontend │ (Chat Interface)
└────────┬────────┘
         │
         │ REST API
         ▼
┌─────────────────┐
│  FastAPI Server │
├─────────────────┤
│ • Chat Router   │
│ • Components    │
│ • LLM Service   │
│ • Validator     │
│ • Compiler      │
└────┬───────┬────┘
     │       │
     │       └─────► Redis (Cache)
     │
     └─────────────► PostgreSQL (Database)
```

## Project Structure

```
spark/
├── frontend/                  # React chat application
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   ├── services/         # API clients
│   │   ├── store/            # Zustand stores
│   │   └── types/            # TypeScript types
│   └── package.json
│
├── backend/                   # FastAPI service
│   ├── app/
│   │   ├── routers/          # API endpoints
│   │   │   ├── chat.py       # Chat & generation
│   │   │   ├── components.py # Component CRUD
│   │   │   └── health.py     # Health checks
│   │   ├── services/         # Business logic
│   │   │   ├── llm.py        # OpenAI integration
│   │   │   ├── validator.py  # Code validation
│   │   │   └── compiler.py   # esbuild wrapper
│   │   ├── middleware/       # Auth & logging
│   │   ├── models/           # Pydantic models
│   │   ├── config.py         # Settings
│   │   ├── database.py       # Database & Redis
│   │   └── main.py           # FastAPI app
│   └── requirements.txt
│
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Local development
└── README.md
```

## Database Schema

### Tables

- **components**: Generated Solid.js components with metadata
- **chat_sessions**: User chat sessions
- **chat_messages**: Conversation history
- **component_executions**: Runtime performance tracking
- **component_feedback**: User ratings (thumbs up/down)
- **audit_logs**: Comprehensive audit trail

All tables have RLS policies for tenant isolation.

## Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (or use Docker)
- OpenAI API key

### Environment Variables

Create `.env` files:

**Backend `.env`:**
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/spark
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-openai-key
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Frontend `.env`:**
```env
VITE_API_URL=http://localhost:8000/api
```

### Local Development

#### Option 1: Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Access the app
open http://localhost:8000
```

#### Option 2: Manual Setup

**Terminal 1 - Redis:**
```bash
docker run -p 6379:6379 redis:7-alpine
```

**Terminal 2 - PostgreSQL:**
```bash
docker run -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_DB=spark postgres:15-alpine
# Note: You need to run migrations manually
```

**Terminal 3 - Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Access frontend at `http://localhost:5173`

### Database Setup

The database schema is automatically created via migration scripts in `database/migrations`. Tables include:

- Components with code, metadata, and compiled bundles
- Chat sessions and message history
- Execution logs and user feedback
- Audit trail for all actions


## Usage

### Chat Interface

1. Open the app in your browser
2. Type a message describing what you want
3. Spark AI will either:
   - Respond with text
   - Generate a Solid.js micro-app component

### Example Prompts

```
"Create a table showing sales data with sorting"
"Build a KPI dashboard with 3 metrics"
"Make a filterable product list"
"Generate a bar chart visualization"
"Show revenue breakdown as a donut chart"
"Create a heatmap of activity over time"
"Compare revenue and orders with a mixed chart"
```

### Available Component Templates

1. **StatCard** - KPI cards with metrics and trends
2. **DataTable** - Filterable, sortable tables
3. **LineChart** - Time-series line charts (ApexCharts)
4. **BarChart** - Comparison bar charts (ApexCharts)
5. **DonutChart** - Category breakdown visualization (ApexCharts)
6. **HeatmapChart** - Time-series intensity heatmap (ApexCharts)
7. **MixedChart** - Combined line + bar charts (ApexCharts)
8. **ListWithSearch** - Searchable item lists
9. **MetricsDashboard** - Multi-metric dashboard with charts

### Component Generation Flow

1. User sends message → Backend
2. LLM analyzes intent → Decides text or component
3. If component:
   - Validate code (AST analysis, forbidden APIs)
   - Compile with esbuild
   - Cache compiled bundle
   - Store in Supabase
   - Return component ID to frontend
4. Frontend displays component in sandboxed iframe

## API Endpoints

### Chat

- `POST /api/chat/message` - Send message, get response

### Components

- `GET /api/components` - List components (paginated)
- `GET /api/components/{id}` - Get component metadata
- `GET /api/components/{id}/artifact` - Download compiled JS
- `GET /api/components/{id}/iframe` - Get iframe HTML
- `POST /api/components/{id}/data` - Data endpoint for iframes (supports `data_mode: "sample" | "real"`)
- `POST /api/components/{id}/data/swap` - Store real data for sample→real swap
- `PUT /api/components/{id}/feedback` - Submit user feedback
- `PUT /api/components/{id}/archive` - Archive component

### Health

- `GET /api/health` - Service health check
- `GET /api/metrics` - Performance metrics

## Security

### Code Validation

Multi-layered validation pipeline:

1. **Syntax Check**: Parse JSX/Solid.js code
2. **AST Analysis**: Scan for forbidden patterns
3. **Import Validation**: Only allow solid-js and apexcharts imports
4. **Size Check**: Enforce 50KB source limit

### Forbidden APIs

Blocked in generated components:

- `window`, `document`, `localStorage`
- `fetch`, `XMLHttpRequest`, `WebSocket`
- `eval`, `Function` constructor
- `innerHTML`, `outerHTML`
- Dynamic imports

### Sandboxing

Components run in iframe with:

- `sandbox="allow-scripts allow-same-origin"`
- Strict Content-Security-Policy
- No access to parent window
- Secure token-based authentication

## Data Bridge Pattern

The Data Bridge enables seamless sample → real data swapping:

1. **Sample Mode** (default): Components fetch mock data for rapid prototyping
2. **Real Mode**: Switch to production data without regenerating components

**Workflow:**
```bash
# 1. Store real data for a component
curl -X POST /api/components/{id}/data/swap \
  -H "Content-Type: application/json" \
  -d '{"mode": "real", "data": {"revenue": [...], "metrics": [...]}}'

# 2. Component automatically refetches when mode changes (via UI toggle or postMessage)
```

**Frontend Integration:**
- Sample/Real toggle in the iframe component
- `postMessage({ type: 'data_swap', mode: 'real' })` triggers refetch
- Components use `createResource` with reactive source for automatic updates

## Performance Targets

- Component generation: < 2s (P95) - **or <200ms with CAG hit**
- Compilation time: 100-300ms
- Compiled bundle: 10-20KB (templates: 10-15KB)
- ApexCharts CDN: ~45KB gzipped (cached)
- CAG lookup: <20ms (content hash database query)
- Cache hit latency: < 50ms
- Chart render time: < 300ms
- Data swap latency: < 100ms
- Time to interactive: < 150ms

## Monitoring

Structured JSON logging for all events:

```json
{
  "timestamp": "2025-11-23T...",
  "event": "component_generated",
  "tenant_id": "org_abc",
  "component_id": "uuid",
  "compile_time_ms": 145,
  "bundle_size_bytes": 9200,
  "cache_hit": false
}
```

Key metrics tracked:

- Generation success rate
- Compilation success rate
- Cache hit rate
- Bundle sizes
- Latencies (P50, P95, P99)

## Deployment

### Docker Build

```bash
# Build production image
docker build -t spark:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=... \
  -e OPENAI_API_KEY=... \
  spark:latest
```

### Production Considerations

- Use managed Redis (AWS ElastiCache, Redis Cloud)
- Configure CORS origins for your domain
- Set up monitoring (Datadog, New Relic)
- Enable rate limiting per tenant
- Use CDN for static assets
- Set appropriate cache TTLs

## Authentication

Currently uses placeholder authentication with headers:

- `X-Tenant-ID`: Organization identifier
- `X-User-ID`: User identifier

**TODO**: Integrate with production auth system (Auth0, etc.)

## Contributing

We welcome contributions! Here's how to get involved:

### Reporting Issues

- **Bug Reports**: Open an issue with steps to reproduce, expected behavior, and actual behavior
- **Feature Requests**: Describe the problem and proposed solution
- **Security Issues**: Email security@kaatu.ai (do NOT open public issues)

### Pull Requests

1. **Fork & Branch**: Create a feature branch from `main`
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes**: Follow existing code style and patterns
   - Backend: Black formatter, type hints, docstrings
   - Frontend: ESLint, Prettier, TypeScript strict mode

3. **Test**: Ensure all tests pass
   ```bash
   # Backend tests
   cd backend && pytest
   
   # Frontend tests
   cd frontend && npm test
   ```

4. **Commit**: Use conventional commits
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation only
   - `refactor:` Code refactoring
   - `test:` Adding tests
   
   Example: `feat: add real-time data streaming support`

5. **Push & PR**: Push to your fork and open a pull request
   - Describe what changed and why
   - Reference related issues
   - Add screenshots for UI changes

### Development Setup

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

### Areas for Contribution

**High Priority:**
- Add more LLM providers (Anthropic Claude, Google Gemini)
- Enhance component library with new templates
- Add WebSocket support for real-time data streaming
- Implement component versioning and rollback
- Create admin dashboard for monitoring

**Good First Issues:**
- Documentation improvements
- Add tests for existing features
- UI/UX enhancements
- Performance optimizations

### Code of Conduct

Be respectful, inclusive, and constructive. Harassment-free experience for everyone.

## License

**Spark is available under a Dual Licensing model.**

### 1. Open Source License (AGPLv3)
This project is licensed under the **GNU Affero General Public License v3 (AGPLv3)**.
- **Allowed:** You can use Spark for free in open-source projects or private experiments.
- **Required:** If you run Spark as a service (internal or external) and integrate it with your application, you **must open-source your connecting application** under a compatible license (AGPL).

### 2. Commercial License (Enterprise)
Want to use Spark in a proprietary/closed-source product without open-sourcing your code?
- **Contact us** to purchase a Commercial License.
- Includes: Enterprise Support, Priority Feature Requests, and Legal Indemnification.
- Email: [enterprise@spark.ai](mailto:enterprise@spark.ai)
