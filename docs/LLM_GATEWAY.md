# LLM Gateway

Spark uses a pluggable LLM Gateway to support multiple providers through a single OpenAI-compatible API. All providers use the OpenAI SDK with different `base_url` and API key configurations.

## Supported Providers

| Provider   | base_url                      | Env Key             |
|------------|-------------------------------|---------------------|
| `openai`   | https://api.openai.com/v1     | `OPENAI_API_KEY`    |
| `openrouter` | https://openrouter.ai/api/v1 | `OPENROUTER_API_KEY` |
| `litellm`  | http://localhost:4000/v1 (default) | `LITELLM_API_KEY` |
| `llmgw`    | Set via `LLMGW_BASE_URL`      | `LLMGW_API_KEY`     |
| `custom`   | Set via `LLM_BASE_URL`        | `LLM_API_KEY`       |

## Configuration

### Environment Variables

```env
LLM_PROVIDER=openai                    # openai | openrouter | litellm | llmgw | custom
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=                           # Or use provider-specific env vars
LLM_BASE_URL=                          # Override for custom/llmgw endpoints
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Provider-specific (alternative to LLM_API_KEY)
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
LITELLM_API_KEY=sk-...
LLMGW_API_KEY=
LLMGW_BASE_URL=                        # Bloomberg LLM Gateway URL

# Fallback (optional)
LLM_FALLBACK_PROVIDER=
LLM_FALLBACK_MODEL=
LLM_FALLBACK_API_KEY=
LLM_FALLBACK_BASE_URL=
```

### Per-Request Override (A2A API)

External agents can override the LLM config per request:

```json
POST /api/a2a/generate
{
  "prompt": "Create a revenue dashboard",
  "llm_config": {
    "provider": "openrouter",
    "model": "anthropic/claude-3.5-sonnet",
    "api_key": "sk-or-..."
  }
}
```

## Usage in Code

```python
from app.services.llm_gateway import LLMGateway, LLMConfig

config = LLMConfig(
    provider="openai",
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

gateway = LLMGateway(config)

response = await gateway.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model=None,  # uses config.model
    temperature=0.7,
)
```

## Fallback

When `LLM_FALLBACK_PROVIDER` is set, the gateway automatically retries on errors using the fallback client.

## Deprecation

`llm_providers.py` is deprecated. Use `llm_gateway.py` and `LLMGateway` for all new code.
