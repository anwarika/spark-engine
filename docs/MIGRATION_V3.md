# Migration Guide: v2.x → v3.0

This guide covers upgrading from Spark v2.x (Solid.js) to Spark v3.0 (React + shadcn/ui).

## Summary of Changes

| Area | v2.x | v3.0 |
|------|------|------|
| Generated apps | Solid.js + ApexCharts | React + shadcn/ui + Recharts |
| LLM abstraction | llm_providers.py | LLMGateway (llm_gateway.py) |
| Chat UI | DaisyUI | shadcn/ui |
| Data Bridge | createResource + window.__DATA_MODE | postMessage `spark_data` |
| Iframe bundle | Solid.js runtime | React CDN + shadcn-ui-bundle.js |

## Breaking Changes

### 1. Generated Component Format

- Components are now React JSX (`.tsx`) instead of Solid.js
- Imports: `react`, `react-dom`, `recharts`, `@/components/ui/*`, `lucide-react`
- No `createResource`, `createSignal`, or Solid primitives

### 2. LLM Configuration

- `LLM_PROVIDER` replaces provider-specific env vars as the primary config
- `llm_providers.py` is deprecated; use `LLMGateway` from `llm_gateway.py`
- A2A accepts `llm_config` for per-request overrides

### 3. Data Bridge

- Old: `createResource(() => window.__DATA_MODE, fetchData)` and `data_swap` postMessage
- New: React components receive `data` prop; parent sends `{ type: 'spark_data', payload: {...} }` to swap data

### 4. Cache Invalidation

- CAG cache keys now include `engine:react`
- Old Solid.js outputs are not reused; regenerated components get new cache entries

## Non-Breaking

- Database schema unchanged
- Redis caching strategy unchanged (only cache key prefix updated)
- Multi-tenant isolation (`X-Tenant-ID`) unchanged
- A2A endpoint URL and basic request shape unchanged; new fields are optional

## Migration Steps

1. **Environment**: Add `LLM_PROVIDER`, `LLM_MODEL` and provider keys to `.env` (see [LLM_GATEWAY.md](LLM_GATEWAY.md)).

2. **Docker**: Rebuild images. The Dockerfile now installs React compiler deps instead of Solid.js.

3. **Frontend**: Run `npm install` in `frontend/`—shadcn/ui is now a dependency. No DaisyUI.

4. **Data Bridge**: If you have custom integrations that send `data_swap`, add support for `spark_data`:
   ```javascript
   iframe.contentWindow.postMessage(
     { type: 'spark_data', payload: realData },
     '*'
   );
   ```

5. **Regenerate components**: Existing Solid.js components in the database continue to render from stored bundles, but new generations will be React. To fully migrate, regenerate components via chat or A2A.

## Rollback

To rollback to v2.x: check out the `v2.x` tag and redeploy. Database and Redis remain compatible.
