"""
LLM Gateway abstraction layer.

Supports:
- openai: Direct OpenAI API
- openrouter: OpenRouter (OpenAI-compatible)
- litellm: LiteLLM proxy (OpenAI-compatible)
- llmgw: Bloomberg internal LLM Gateway (OpenAI-compatible)
- custom: Any OpenAI-compatible endpoint

All providers use the OpenAI SDK with different base_url/api_key configs.
"""
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel
import os


class LLMConfig(BaseModel):
    provider: str = "openai"  # openai | openrouter | litellm | llmgw | custom
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    # Provider-specific
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: Optional[str] = None
    # Fallback config
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    fallback_api_key: Optional[str] = None
    fallback_base_url: Optional[str] = None


class LLMGateway:
    """
    Unified LLM gateway. Every provider is just an OpenAI client
    with a different base_url.
    """

    PROVIDER_DEFAULTS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
        },
        "litellm": {
            "base_url": "http://localhost:4000/v1",
            "env_key": "LITELLM_API_KEY",
        },
        "llmgw": {
            "base_url": None,  # Must be set via LLMGW_BASE_URL
            "env_key": "LLMGW_API_KEY",
        },
        "custom": {
            "base_url": None,  # Must be set via config
            "env_key": "CUSTOM_LLM_API_KEY",
        },
    }

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = self._build_client(config)
        self.fallback_client = None
        if config.fallback_provider:
            fallback_config = LLMConfig(
                provider=config.fallback_provider,
                model=config.fallback_model or config.model,
                api_key=config.fallback_api_key,
                base_url=config.fallback_base_url,
            )
            self.fallback_client = self._build_client(fallback_config)

    def _build_client(self, config: LLMConfig) -> AsyncOpenAI:
        defaults = self.PROVIDER_DEFAULTS.get(config.provider, {})
        api_key = config.api_key or os.getenv(defaults.get("env_key", ""), "")
        base_url = config.base_url or os.getenv(
            f"{config.provider.upper()}_BASE_URL",
            defaults.get("base_url"),
        )
        extra_headers = {}
        if config.provider == "openrouter":
            if config.openrouter_site_url:
                extra_headers["HTTP-Referer"] = config.openrouter_site_url
            if config.openrouter_app_name:
                extra_headers["X-Title"] = config.openrouter_app_name

        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers or None,
        )

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        """Non-streaming chat completion."""
        try:
            return await self._call(self.client, messages, **kwargs)
        except Exception:
            if self.fallback_client:
                return await self._call(self.fallback_client, messages, **kwargs)
            raise

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator:
        """Streaming chat completion."""
        try:
            async for chunk in self._call_stream(self.client, messages, **kwargs):
                yield chunk
        except Exception:
            if self.fallback_client:
                async for chunk in self._call_stream(
                    self.fallback_client, messages, **kwargs
                ):
                    yield chunk
            else:
                raise

    async def _call(self, client: AsyncOpenAI, messages, **kwargs):
        response = await client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ("model", "temperature", "max_tokens")
            },
        )
        return response

    async def _call_stream(self, client: AsyncOpenAI, messages, **kwargs):
        response = await client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            stream=True,
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ("model", "temperature", "max_tokens")
            },
        )
        async for chunk in response:
            yield chunk
