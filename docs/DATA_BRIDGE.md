# Data Bridge: Sample → Real Data Swapping

The Data Bridge pattern enables seamless transitions from mock/sample data to real production data without regenerating components.

**v3.0 (React):** Components receive a `data` prop. The iframe listens for `{ type: 'spark_data', payload: {...} }` postMessage and re-renders with the new data. See [React Data Bridge](#react-data-bridge-v30) below.

## Concept

When developing dashboards and visualizations, you often want to:

1. **Prototype quickly** with sample data
2. **Review and approve** the UI/UX
3. **Connect to real data** without rebuilding

The Data Bridge makes this workflow seamless.

## Architecture

```
┌─────────────────┐
│   Component     │
│  (Solid/v2 or React/v3)
└────────┬────────┘
         │ v2: createResource(source, fetchData)
         │ v3: data prop + spark_data postMessage
         ▼
┌─────────────────┐
│  /data endpoint │
├─────────────────┤
│ if mode=real:   │
│   return stored │
│ else:           │
│   return mock   │
└─────────────────┘
```

**Key Components:**

1. **v2 (Solid.js):** `window.__DATA_MODE`, `createResource(() => window.__DATA_MODE, fetchData)`
2. **v3 (React):** `data` prop; iframe listens for `spark_data` postMessage and re-renders
3. **Redis Storage**: Real data stored with TTL (1 hour)
4. **postMessage API**: Parent triggers swap; v3 uses `{ type: 'spark_data', payload }`

## Usage

### Basic Flow

```javascript
// 1. Component loads with sample data (automatic)
const [data] = createResource(
  function() { return window.__DATA_MODE || 'sample'; },
  fetchData
);

// 2. fetchData respects the mode
async function fetchData() {
  const dataMode = window.__DATA_MODE || 'sample';
  const response = await fetch('/api/components/' + window.__COMPONENT_ID + '/data', {
    method: 'POST',
    body: JSON.stringify({ 
      mock: { profile: 'ecommerce' },
      data_mode: dataMode 
    })
  });
  return response.json();
}

// 3. When window.__DATA_MODE changes, component refetches automatically
```

### Server-Side Storage

Store real data for a component:

```bash
POST /api/components/{component_id}/data/swap
Content-Type: application/json

{
  "mode": "real",
  "data": {
    "products": [
      {"id": 1, "name": "Widget", "price": 29.99},
      ...
    ],
    "metrics": [
      {"date": "2026-02-01", "revenue": 10000},
      ...
    ],
    "summary": {
      "total_revenue": 50000,
      "total_orders": 234
    }
  }
}
```

**Storage Details:**
- **Redis Key**: `databridge:{tenant_id}:{component_id}:real`
- **TTL**: 1 hour (3600 seconds)
- **Format**: JSON string
- **Isolation**: Tenant-scoped for security

### Client-Side Swap

Trigger the swap from the React parent:

```typescript
import { useRef } from 'react';

function MyApp() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  const swapToRealData = () => {
    // Option 1: Using the UI toggle (built-in)
    // User clicks "Real" button in MicroappIframe
    
    // Option 2: Programmatic swap
    iframeRef.current?.contentWindow?.postMessage(
      { type: 'data_swap', mode: 'real' },
      '*'
    );
  };
  
  return (
    <MicroappIframe 
      ref={iframeRef}
      componentId={id}
    />
  );
}
```

### Inline Swap (Without Backend Storage)

Pass real data directly via postMessage:

```typescript
// v2 (Solid.js)
iframeRef.current?.contentWindow?.postMessage(
  { type: 'data_swap', mode: 'real', data: { metrics: actualMetrics, ... } },
  '*'
);

// v3 (React) — preferred
iframeRef.current?.contentWindow?.postMessage(
  { type: 'spark_data', payload: { metrics: actualMetrics, summary: actualSummary } },
  '*'
);
```

**Note:** This approach stores data in the iframe's context but won't persist. Use `/data/swap` for persistent storage.

### React Data Bridge (v3.0)

v3 React components accept a `data` prop. The iframe HTML template listens for `spark_data` messages and re-renders:

```typescript
// Parent sends data
iframeRef.current?.contentWindow?.postMessage(
  { type: 'spark_data', payload: realData },
  '*'
);

// Generated component receives data via props
export default function MyChart({ data = sampleData }: { data?: ChartData }) {
  return <BarChart data={data?.series ?? []} />;
}
```

Theme sync: send `{ type: 'spark_theme', theme: 'dark' | 'light' }` to toggle dark mode in the iframe.

## Data Schema Validation

When storing real data, ensure it matches the expected structure:

### E-commerce Profile

```json
{
  "products": [{"id": 1, "name": "...", "category": "...", "price": 0}],
  "metrics": [{"date": "...", "revenue": 0, "conversions": 0}],
  "summary": {"total_revenue": 0, "total_orders": 0}
}
```

### SaaS Profile

```json
{
  "accounts": [{"id": 1, "name": "...", "mrr": 0}],
  "metrics": [{"date": "...", "mrr": 0, "churn_rate": 0}],
  "summary": {"mrr": 0, "arr": 0}
}
```

### Validation Helpers

Use the Python utility for validation:

```python
from app.models.data_schema import validate_data_shape

result = validate_data_shape(
    data={"products": [...]}, 
    expected_keys=["products", "metrics", "summary"]
)

if not result["valid"]:
    print(f"Missing keys: {result['missing']}")
```

## Frontend Integration

### Using the Built-in Toggle

The `MicroappIframe` component now includes a Sample/Real toggle:

```tsx
<MicroappIframe 
  componentId={componentId}
  onFeedback={handleFeedback}
/>
```

The toggle appears at the top of the iframe card with a mode indicator badge.

### Custom Integration

Build your own data swap UI:

```tsx
import { useState } from 'react';
import axios from 'axios';

function CustomDataBridge({ componentId, iframeRef }) {
  const [mode, setMode] = useState<'sample' | 'real'>('sample');
  
  const swapToReal = async (realData: any) => {
    // Store real data
    await axios.post(`/api/components/${componentId}/data/swap`, {
      mode: 'real',
      data: realData
    });
    
    // Trigger iframe refetch
    iframeRef.current?.contentWindow?.postMessage(
      { type: 'data_swap', mode: 'real' },
      '*'
    );
    
    setMode('real');
  };
  
  return (
    <button onClick={() => swapToReal(myRealData)}>
      Load Production Data
    </button>
  );
}
```

## A2A Protocol Updates

The A2A protocol now supports data context:

```bash
POST /api/a2a/generate
{
  "prompt": "Create a revenue dashboard",
  "data_context": {
    "revenue": [{"month": "Jan", "value": 50000}, ...]
  }
}
```

When `data_context` is provided:
1. Component is generated with appropriate data profile
2. Data is stored via `/data/swap` as real data
3. Component loads with real data immediately

## Performance

**Data Swap Latency:**
- Mode toggle: <50ms (UI update)
- postMessage: <10ms
- Redis lookup: <20ms
- Component refetch: <100ms
- Chart re-render: <300ms
- **Total: <500ms**

**Storage:**
- Real data is cached in Redis (1 hour TTL)
- Automatic eviction after TTL
- Per-tenant isolation

## Troubleshooting

### Component Doesn't Refetch After Swap

**Symptom:** Clicking "Real" toggle doesn't update the chart.

**Cause:** Component doesn't use reactive source.

**Fix:** Ensure `createResource` uses a source:

```javascript
// ❌ Wrong - no reactive source
const [data] = createResource(fetchData);

// ✅ Correct - reactive source triggers refetch
const [data] = createResource(
  function() { return window.__DATA_MODE || 'sample'; },
  fetchData
);
```

### Real Data Not Found

**Symptom:** Component shows mock data even in "Real" mode.

**Cause:** Real data hasn't been stored yet.

**Fix:** POST to `/data/swap` before switching:

```bash
curl -X POST http://localhost:8000/api/components/{id}/data/swap \
  -H "X-Tenant-ID: your-tenant" \
  -d '{"mode": "real", "data": {...}}'
```

### Cross-Origin postMessage Error

**Symptom:** postMessage blocked by browser security.

**Cause:** Origin mismatch between parent and iframe.

**Fix:** Use wildcard origin for development:

```typescript
iframeRef.current?.contentWindow?.postMessage(
  { type: 'data_swap', mode: 'real' },
  '*'  // Allow all origins (dev only)
);
```

For production, specify exact origin:
```typescript
postMessage(msg, 'https://yourdomain.com');
```

## Advanced: Context-Based Approach

For custom components that need direct context access:

```javascript
import { useContext } from 'solid-js';

export default function MyComponent() {
  // Access the Data Bridge context
  const DataContext = window.DataContext;
  
  if (DataContext) {
    const ctx = useContext(DataContext);
    const bridgeData = ctx?.data;  // Signal
    const bridgeMode = ctx?.mode;  // Signal
    
    // Use context data directly
    return (
      <div>
        <p>Mode: {bridgeMode()}</p>
        <p>Data: {JSON.stringify(bridgeData())}</p>
      </div>
    );
  }
  
  // Fallback to createResource
  const [data] = createResource(fetchData);
  return <div>{/* ... */}</div>;
}
```

## Security Considerations

1. **Tenant Isolation**: Real data is stored with tenant prefix
2. **Redis TTL**: Auto-expiration prevents data leaks
3. **Access Control**: `/data/swap` requires tenant authentication
4. **No Client Persistence**: Data is server-side only (Redis)

## Backward Compatibility

- **v1.x components**: Continue working with sample data only
- **API compatibility**: All v1.x endpoints unchanged
- **Database**: No migration required
- **Frontend**: v1.x components render normally but lack data toggle

To enable Data Bridge for v1.x components: **regenerate them** via chat.
