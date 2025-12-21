# Spark - AI-Powered Micro App Generation Service

Spark is a standalone service that generates, validates, and serves dynamic Solid.js micro-apps through a chat interface. Users interact with an LLM that decides whether to respond with text or generate a Solid.js component. Generated components are compiled, validated, sandboxed, cached, and served to the frontend.

## Developer Quickstart (5 Minutes)

Want to add "Generate UI" capabilities to your own AI agent or chat app?

1.  **Clone & Run**
    ```bash
    git clone https://github.com/your-org/spark.git
    cd spark
    # Set your LLM Key
    export OPENAI_API_KEY=sk-... 
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

## Features

- **LLM-Powered Generation**: OpenAI GPT-4o-mini generates optimized Solid.js components on demand
- **Multi-Layered Security**: AST analysis, forbidden API detection, and sandboxed execution
- **High Performance**: Redis caching, esbuild compilation, and Solid.js's minimal runtime
- **Multi-Tenant Architecture**: Complete tenant isolation with Supabase RLS
- **Chat Interface**: Clean React + DaisyUI UI for natural interaction
- **Component Registry**: Store, version, and manage generated components

## Tech Stack

### Frontend
- React + TypeScript
- DaisyUI + Tailwind CSS
- Zustand (state management)
- Axios (API client)

### Generated Micro Apps
- Solid.js + TypeScript
- DaisyUI for styling
- Sandboxed iframe execution

### Backend
- FastAPI + Python 3.11+
- OpenAI API (GPT-4o-mini)
- esbuild (Solid.js compilation)
- Supabase (PostgreSQL database)
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
     └─────────────► Supabase (Database)
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
│   │   ├── database.py       # Supabase & Redis
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
- Supabase account
- OpenAI API key

### Environment Variables

Create `.env` files:

**Backend `.env`:**
```env
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-openai-key
ENVIRONMENT=development
LOG_LEVEL=INFO

# Optional: Appsmith auto-create (experimental, local/dev)
# Spark can sign in to Appsmith and create a new scaffold app + pages.
# Requires you to create an Appsmith user first by visiting http://localhost:8080 and signing up.
APPSMITH_AUTOCREATE_ENABLED=false
APPSMITH_PUBLIC_URL=http://localhost:8080
APPSMITH_INTERNAL_URL=http://appsmith:80
APPSMITH_EMAIL=you@example.com
APPSMITH_PASSWORD=your-password
```

**Note:** The `SUPABASE_SERVICE_ROLE_KEY` is required for development to bypass RLS policies. Find it in your Supabase project: **Settings → API → Project API keys → `service_role`** (secret).

**Frontend `.env`:**
```env
VITE_API_URL=http://localhost:8000/api
```

### Appsmith Auto-Create (Optional)

Spark can optionally auto-create an Appsmith app (and basic pages) when the LLM chooses `appsmith_app`.

- **One-time setup**: open `http://localhost:8080` and create an Appsmith user (signup).
- **Enable in Spark**: set `APPSMITH_AUTOCREATE_ENABLED=true` plus `APPSMITH_EMAIL` / `APPSMITH_PASSWORD`.
- **Docker note**: the backend talks to Appsmith via `APPSMITH_INTERNAL_URL` (defaults to `http://appsmith:80` in `docker-compose.yml`). Don’t point it at `http://localhost:8080` unless you’re running the backend outside docker.
- **Security note**: this uses Appsmith session auth (cookies + XSRF) and is intended for local/dev.

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

**Terminal 2 - Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Access frontend at `http://localhost:5173`

### Database Setup

The Supabase schema is automatically created via migration. Tables include:

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
```

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
- `POST /api/components/{id}/data` - Data endpoint for iframes
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
3. **Import Validation**: Only allow solid-js imports
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

## Performance Targets

- Component generation: < 2s (P95)
- Compilation time: 100-300ms
- Compiled bundle: 10-20KB
- Cache hit latency: < 50ms
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
  -e SUPABASE_URL=... \
  -e SUPABASE_ANON_KEY=... \
  -e SUPABASE_SERVICE_ROLE_KEY=... \
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

**TODO**: Integrate with production auth system (Supabase Auth, Auth0, etc.)

## Contributing

This is a reference implementation. To extend:

1. Add more LLM providers (OpenAI, etc.)
2. Enhance component library with pre-built templates
3. Add real-time collaboration features
4. Implement component versioning
5. Create admin dashboard for monitoring

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
