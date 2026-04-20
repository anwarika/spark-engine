# Spark Quickstart

Get from zero to a live Spark widget in your chat app in **< 5 minutes**.

---

## Prerequisites

- Spark backend running (see [Docker setup](#docker-setup))
- Node.js 18+ for the SDK

---

## 1. Start Spark

```bash
# Clone and start with Docker
git clone https://github.com/your-org/spark-engine
cd spark-engine
docker-compose up -d
```

Spark starts on `http://localhost:8000`. Verify with:

```bash
curl http://localhost:8000/api/health
# { "status": "healthy", "version": "3.3.0", ... }
```

Open the **Playground** at `http://localhost:5173` to try it immediately — no auth required for the default dev tenant.

---

## 2. Create an API Key

```bash
# With header auth (dev mode — no key needed yet)
curl -X POST http://localhost:8000/api/keys \
  -H "X-Tenant-ID: my-app" \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"label": "Production key", "scopes": ["generate", "read", "pin", "admin"]}'
```

Response (save the `key` — it is shown **once**):

```json
{
  "id": "abc123...",
  "key": "sk_live_<your-key-is-shown-here-only-once>",
  "label": "Production key",
  "scopes": ["generate", "read", "pin", "admin"]
}
```

---

## 3. Generate your first component

```bash
curl -X POST http://localhost:8000/api/a2a/generate \
  -H "Authorization: Bearer YOUR_SPARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a sales pipeline dashboard with deal stages and win rates"}'
```

Response:

```json
{
  "status": "success",
  "component_id": "comp_abc123",
  "microapp_url": "http://localhost:8000/api/components/comp_abc123/iframe"
}
```

Drop `microapp_url` into an `<iframe>` — that's your live widget.

---

## 4. Embed with the SDK

Install:

```bash
npm install @spark-engine/sdk
```

### React (recommended)

```tsx
import { SparkWidget } from '@spark-engine/sdk';

// The simplest possible usage — SparkWidget handles loading skeleton + errors
export function ChatMessage({ componentId }: { componentId: string }) {
  return (
    <SparkWidget
      iframeUrl={`http://localhost:8000/api/components/${componentId}/iframe`}
      style={{ height: 400, borderRadius: 12, overflow: 'hidden' }}
    />
  );
}
```

### Generate and embed in one call

```tsx
import { SparkClient } from '@spark-engine/sdk';

const spark = new SparkClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'YOUR_SPARK_API_KEY',
});

// In your chat message handler:
async function handleUserMessage(message: string) {
  // generateAndWait combines generate() + iframeUrl() in one call
  const iframeUrl = await spark.generateAndWait({ prompt: message });
  return iframeUrl; // ready to put in <SparkWidget iframeUrl={...} />
}
```

### Error handling

```tsx
import { SparkRateLimitError, SparkGenerationError } from '@spark-engine/sdk';

try {
  const url = await spark.generateAndWait({ prompt });
} catch (e) {
  if (e instanceof SparkRateLimitError) {
    // Wait e.retryAfter seconds, then retry
    await delay(e.retryAfter * 1000);
  } else if (e instanceof SparkGenerationError) {
    // Show "Try rephrasing your request" UI
  }
}
```

---

## 5. Pin a component (stable bookmarks)

Pinned apps survive regeneration — the pin ID stays stable even when the underlying component is refreshed.

```tsx
// Pin the generated component
const pin = await spark.pinApp({
  component_id: componentId,
  slot_name: 'Sales Pipeline',
  icon: '📊',
});

// Later: regenerate with a new prompt (pin ID stays the same)
await spark.regeneratePin(pin.id, { prompt: 'Update with Q2 data' });
```

---

## 6. Push real data (Data Bridge)

Instead of regenerating, push live data into a running component:

```tsx
// After the component is displayed, swap in real data
await spark.pushData(componentId, {
  deals: fetchedDeals,
  metrics: fetchedMetrics,
});

// For partial updates (merge into existing data):
await fetch(`/api/components/${componentId}/data`, {
  method: 'PATCH',
  headers: { Authorization: `Bearer YOUR_SPARK_API_KEY` },
  body: JSON.stringify({ data: { deals: newDeals }, ttl_seconds: 7200 }),
});
```

---

## 7. Check usage (Admin)

```bash
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer YOUR_SPARK_API_KEY"
```

Or open the **Admin** tab in the frontend at `http://localhost:5173`.

---

## Next steps

- [Integration guide](./INTEGRATION.md) — OpenAI GPTs, LangChain, Vercel AI SDK
- [Data Bridge](./DATA_BRIDGE.md) — sample → real data patterns
- [SDK reference](../packages/spark-sdk/README.md)
- [Examples](../examples/) — Next.js chat, plain JS embed

---

## Docker setup

```yaml
# docker-compose.yml (included in repo)
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: spark
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/spark
      REDIS_URL: redis://redis:6379
      LLM_PROVIDER: openai
      OPENAI_API_KEY: sk-...   # your key here
    depends_on: [db, redis]
```

```bash
docker-compose up -d
# Run migrations
docker-compose exec backend python -m alembic upgrade head
# (or apply SQL files in database/migrations/ manually)
```
