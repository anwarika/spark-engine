# Spark Quickstart Guide

## Prerequisites

Install the following:
- Node.js 20+ and npm
- Python 3.11+
- Docker and Docker Compose

## Quick Setup

### 1. Environment Setup

The Supabase database is already configured and the schema has been created. Configure your backend environment variables (including your LLM API key):

```bash
# Edit backend/.env and add your API keys
cd backend
# Update OPENAI_API_KEY (required) in .env
```

### (Optional) Appsmith Auto-Create Setup

If you want Spark to **auto-create** an Appsmith app from your prompt (instead of just opening Appsmith), do this once:

1. Start services with docker compose (see below), then open Appsmith at `http://localhost:8080` and **sign up** (create the first user).
2. Enable auto-create by setting these environment variables:
   - `APPSMITH_AUTOCREATE_ENABLED=true`
   - `APPSMITH_EMAIL=...`
   - `APPSMITH_PASSWORD=...`

For docker compose, put those values in the **project-root** `.env` so `docker-compose.yml` can pass them into the backend container. For manual backend dev, put them in `backend/.env`.

### 2. Option A: Docker Compose (Recommended)

```bash
# From project root
docker-compose up --build
```

Access the app at: http://localhost:8000

### 3. Option B: Manual Development

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

Access frontend at: http://localhost:5173

## Testing the Application

1. Open the chat interface
2. Try example prompts:
   - "Create a data table with sorting"
   - "Build a KPI dashboard"
   - "Make a filterable list"

## Database

The database schema has been automatically created in Supabase with the following tables:
- `components` - Generated micro-apps
- `chat_sessions` - User sessions
- `chat_messages` - Conversation history
- `component_executions` - Performance metrics
- `component_feedback` - User ratings
- `audit_logs` - Action tracking

## Architecture Overview

```
User → React Chat UI → FastAPI Backend → Claude LLM
                     ↓
                     Validator → Compiler → Supabase
                     ↓
                     Redis Cache
```

## Key Files

- `backend/app/main.py` - FastAPI entry point
- `backend/app/routers/chat.py` - Chat & generation logic
- `backend/app/services/llm.py` - Claude AI integration
- `backend/app/services/validator.py` - Security validation
- `backend/app/services/compiler.py` - esbuild compilation
- `frontend/src/components/ChatWindow.tsx` - Chat UI
- `frontend/src/components/ComponentIframe.tsx` - Sandboxed component renderer

## Troubleshooting

### Backend won't start
- Check that Redis is running
- Verify SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env
- Ensure Python dependencies are installed

### Frontend build fails
- Run `npm install` in frontend/ directory
- Check that Node.js 20+ is installed
- Clear node_modules and reinstall if needed

### Components won't compile
- Ensure esbuild is installed globally: `npm install -g esbuild`
- Check that Node.js is available in the backend container

### Database connection issues
- Verify Supabase credentials are correct
- Check that the database schema migration was applied
- Test connection: `psql your-connection-string`

## Next Steps

1. Add your Anthropic API key to start generating components
2. Customize the LLM system prompt in `backend/app/services/llm.py`
3. Extend the component library with pre-built templates
4. Implement production authentication
5. Set up monitoring and logging infrastructure

## Documentation

See [README.md](README.md) for complete documentation including:
- Full API reference
- Security architecture
- Performance optimization
- Production deployment guide
