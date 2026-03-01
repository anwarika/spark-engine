"""
DEPRECATED: Use app.services.llm_gateway.LLMGateway instead.

This module is kept for reference. LLMService now uses LLMGateway with
configurable OpenAI-compatible providers (openai, openrouter, litellm, llmgw, custom).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models import ChatResponse
import os
import json


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        **kwargs
    ) -> ChatResponse:
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def get_provider_name(self) -> str:
        return "openai"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        **kwargs
    ) -> ChatResponse:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                response_format={"type": "json_object"},
                max_completion_tokens=4096,
                **kwargs
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            return ChatResponse(
                type=parsed.get("type", "text"),
                content=parsed.get("content", ""),
                reasoning=parsed.get("reasoning", "")
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def get_provider_name(self) -> str:
        return "anthropic"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        **kwargs
    ) -> ChatResponse:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_completion_tokens=4096,
                system=system_prompt,
                messages=messages,
                **kwargs
            )
            
            content = response.content[0].text
            # Anthropic doesn't force JSON structure as strictly as OpenAI's json_object mode
            # We might need to try/except parsing or prompt engineering to ensure JSON
            try:
                parsed = json.loads(content)
                return ChatResponse(
                    type=parsed.get("type", "text"),
                    content=parsed.get("content", ""),
                    reasoning=parsed.get("reasoning", "")
                )
            except json.JSONDecodeError:
                # Fallback text handling
                return ChatResponse(type="text", content=content, reasoning="Anthropic Fallback")
                
        except Exception as e:
             raise Exception(f"Anthropic API error: {str(e)}")

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = model

    def get_provider_name(self) -> str:
        return "openrouter"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        **kwargs
    ) -> ChatResponse:
        # Same interface as OpenAI
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                response_format={"type": "json_object"}, # OpenRouter supports this for many models
                max_completion_tokens=4096,
                **kwargs
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return ChatResponse(
                type=parsed.get("type", "text"),
                content=parsed.get("content", ""),
                reasoning=parsed.get("reasoning", "")
            )
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")


