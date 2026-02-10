# Content-Addressable Generation (CAG)

CAG is Spark's intelligent component deduplication system that prevents regenerating identical micro-apps.

## Overview

When users request similar components, CAG:
1. **Normalizes** the prompt (lowercasing, synonym replacement, whitespace normalization)
2. **Computes a content hash** from: normalized prompt + template + data profile
3. **Checks** if a component with that hash already exists
4. **Returns** the existing component instantly (no LLM call, ~1500ms saved)

## Architecture

```
User Prompt
    │
    ├─> Normalize → "show sales chart" → "show sales chart"
    ├─> Hash → SHA256(prompt|template|profile)
    │
    ├─> DB Lookup (content_hash)
    │
    ├─> FOUND? ──YES──> Return existing component (CAG HIT)
    │            │
    │            NO───> Generate via LLM (CAG MISS)
    │                   └─> Store with content_hash
```

## Key Components

### 1. Content Fingerprint

```python
{
  "content_hash": "a3f8b2c...",  # SHA256 of canonical form
  "normalized_prompt": "show sales chart",
  "template_name": "LineChart",
  "data_profile": "ecommerce"
}
```

### 2. Database Schema

```sql
ALTER TABLE components ADD COLUMN content_hash TEXT;
ALTER TABLE components ADD COLUMN prompt_normalized TEXT;
ALTER TABLE components ADD COLUMN generation_metadata JSONB;

CREATE INDEX idx_components_content_hash ON components(content_hash);
CREATE INDEX idx_components_cag_lookup ON components(tenant_id, content_hash, status);
```

### 3. Normalization Rules

| Input | Normalized |
|-------|------------|
| "Show me sales" | "show sales" |
| "Display a chart of revenue" | "show chart revenue" |
| "Create bar graph" | "create bar chart" |
| "Generate   table  " | "create table" |

**Synonym Groups:**
- **show**: display, show me
- **create**: generate, make, build, create
- **chart**: graph, visualization, chart

## Usage

### Automatic (Default)

CAG runs automatically on every `/api/chat/message` request:

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "X-Tenant-ID: acme" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-123",
    "message": "Show me a line chart of revenue"
  }'
```

**First call:** CAG MISS → generates component → stores hash
**Second call (same prompt):** CAG HIT → returns existing component (~1500ms faster)

### Manual Search

Find components by content hash:

```bash
curl "http://localhost:8000/api/components/search?content_hash=a3f8b2c..." \
  -H "X-Tenant-ID: acme"
```

Response:
```json
{
  "components": [{
    "id": "uuid",
    "content_hash": "a3f8b2c...",
    "prompt_normalized": "show revenue chart",
    "generation_metadata": {
      "reuse_count": 5,
      "template_name": "LineChart"
    },
    "created_at": "2026-02-10T12:00:00Z"
  }],
  "total": 1
}
```

## Performance Impact

### CAG HIT (component exists)
- **Time saved**: ~1500ms (no LLM generation)
- **Cost saved**: $0.001-0.003 per request
- **Response time**: ~50-100ms (database lookup only)

### CAG MISS (new component)
- **Overhead**: +10-20ms (hash computation + lookup)
- **Total time**: Standard generation time + 10-20ms

### Metrics Example

```json
{
  "event": "cag_hit",
  "component_id": "uuid",
  "content_hash": "a3f8b2c",
  "normalized_prompt": "show revenue chart",
  "reuse_count": 5,
  "timing": {
    "cag_lookup_ms": 15,
    "total_ms": 85
  }
}
```

## Reuse Tracking

Each component tracks reuse count:

```json
{
  "generation_metadata": {
    "reuse_count": 12,
    "template_name": "LineChart",
    "data_profile": "ecommerce",
    "original_component_id": null
  }
}
```

## API Endpoints

### GET `/api/components/search`

Search for components by content hash.

**Query Parameters:**
- `content_hash` (required): SHA256 hash to search for
- `limit` (optional): Max results (default: 20, max: 100)

### GET `/api/cag/metrics`

Get CAG performance metrics.

**Response:**
```json
{
  "tenant_id": "acme",
  "metrics": {
    "total_components": 150,
    "cag_enabled": true,
    "hit_rate": 0.42,
    "total_reuses": 63,
    "avg_time_saved_ms": 1500
  }
}
```

## Configuration

CAG is enabled by default with no configuration needed.

**Normalization customization** (in `backend/app/services/cag.py`):

```python
synonyms = {
    r'\bchart\b': 'chart',
    r'\bgraph\b': 'chart',
    # Add more synonyms here
}
```

## Debugging

### Check if CAG is working

Look for log entries:

```bash
docker-compose logs backend | grep -E "CAG (HIT|MISS)"
```

**CAG HIT:**
```json
{
  "event": "cag_hit",
  "content_hash": "a3f8b2c",
  "normalized_prompt": "show revenue chart",
  "timing": {"total_ms": 85}
}
```

**CAG MISS:**
```json
{
  "event": "micro_app_created",
  "cache_strategy": "cag_miss_llm_generated",
  "cag_metrics": {
    "content_hash": "b7e4d1f",
    "normalized_prompt": "create donut chart category",
    "cag_hit": false
  }
}
```

### Test CAG manually

```bash
# 1. Send first request
curl -X POST http://localhost:8000/api/chat/message \
  -H "X-Tenant-ID: test" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "message": "show sales chart"}'

# 2. Send identical request (should hit CAG)
curl -X POST http://localhost:8000/api/chat/message \
  -H "X-Tenant-ID: test" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s2", "message": "show sales chart"}'

# 3. Check logs
docker-compose logs backend | tail -20 | grep CAG
```

Expected output:
```
CAG MISS: No existing component for hash a3f8b2c..., generating new
CAG HIT: Reusing component uuid for prompt hash a3f8b2c...
```

## Best Practices

### For Users

1. **Be consistent**: "Show sales chart" and "show sales chart" will hit CAG, but "Display sales graph" might not (depends on normalization).

2. **Reuse prompts**: If you frequently need the same type of component, use the exact same prompt.

3. **Check reuse count**: High reuse counts indicate well-designed, frequently needed components.

### For Developers

1. **Expand synonyms**: Add common synonyms to `CAGService.normalize_prompt()` based on usage patterns.

2. **Monitor hit rate**: Low hit rates (<20%) suggest poor normalization or too much prompt variation.

3. **Tune granularity**: Balance between:
   - **Too coarse**: Different prompts collide (wrong reuse)
   - **Too fine**: Similar prompts don't match (missed reuse)

## Limitations

1. **Cross-profile misses**: Same prompt with different data profiles (ecommerce vs saas) won't hit.

2. **Tenant isolation**: Components are never shared across tenants (security).

3. **Template changes**: If you update a template, old components with that template's hash remain unchanged.

4. **Semantic similarity**: CAG uses exact string matching after normalization, not semantic similarity (no embeddings/vectors).

## Future Enhancements

- **Semantic search**: Use embeddings to find similar prompts
- **Cross-tenant templates**: Public component library
- **Automatic synonym learning**: ML-based synonym expansion
- **Smart invalidation**: Detect when templates change and refresh hashes
- **A/B testing**: Compare CAG on vs off performance

## Troubleshooting

### CAG always misses

**Check:**
1. Database migration ran: `SELECT content_hash FROM components LIMIT 1;`
2. Index exists: `\d components` should show `idx_components_content_hash`
3. Logs show hash computation: `grep "content_hash" logs`

### False positives (wrong component returned)

**Cause**: Hash collision or overly broad normalization

**Fix**: Refine `normalize_prompt()` to preserve more intent

### Performance regression

**Check**: `timing.cag_lookup_ms` in logs should be <20ms

**Fix**: If slow, check database indexes and query performance

## Related Documentation

- [Data Bridge Pattern](DATA_BRIDGE.md) - Sample→real data swapping
- [Migration Guide](MIGRATION_V2.md) - Upgrading to v2.0
- [Performance Tuning](../README.md#performance-targets) - Optimization guidelines
