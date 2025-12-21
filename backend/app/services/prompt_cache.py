"""LLM Prompt caching service for avoiding redundant component generation."""

import hashlib
import json
import logging
import re
from typing import Optional

from app.database import get_redis
from app.models import ChatResponse

logger = logging.getLogger(__name__)


class PromptCache:
    """
    Cache LLM responses based on semantic similarity of prompts.
    Avoids regenerating components for similar requests.
    """

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        self.ttl_seconds = ttl_seconds
        self.cache_prefix = "llm:prompt:"

    def _normalize_prompt(self, prompt: str) -> str:
        """
        Normalize a prompt for caching by:
        1. Converting to lowercase
        2. Removing punctuation
        3. Removing extra whitespace
        4. Extracting key terms
        """
        # Lowercase
        normalized = prompt.lower()
        
        # Remove URLs
        normalized = re.sub(r'https?://\S+', '', normalized)
        
        # Keep only alphanumeric and spaces
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Extract key terms (chart types, data types, actions)
        key_terms = []
        
        # Chart types
        chart_keywords = ['chart', 'graph', 'plot', 'line', 'bar', 'pie', 'area', 'scatter']
        for keyword in chart_keywords:
            if keyword in normalized:
                key_terms.append(keyword)
        
        # Data types
        data_keywords = ['revenue', 'sales', 'orders', 'users', 'customers', 'products', 
                        'metrics', 'kpi', 'dashboard', 'table', 'list', 'trend']
        for keyword in data_keywords:
            if keyword in normalized:
                key_terms.append(keyword)
        
        # Actions
        action_keywords = ['show', 'display', 'visualize', 'create', 'build', 'generate']
        for keyword in action_keywords:
            if keyword in normalized:
                key_terms.append(keyword)
        
        # Profile hints
        profile_keywords = ['ecommerce', 'saas', 'marketing', 'finance', 'sales', 'mrr', 'pipeline']
        for keyword in profile_keywords:
            if keyword in normalized:
                key_terms.append(keyword)
        
        # Combine normalized prompt with key terms for better matching
        if key_terms:
            normalized = ' '.join(key_terms) + ' ' + normalized
        
        return normalized

    def compute_prompt_hash(self, prompt: str, profile: str = "general") -> str:
        """
        Compute a hash for the prompt that captures semantic meaning.
        Similar prompts should produce similar hashes.
        """
        normalized = self._normalize_prompt(prompt)
        combined = f"{profile}:{normalized}"
        
        # Use first 16 chars of hash for reasonable key length
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    async def get_cached_response(
        self, prompt: str, profile: str = "general"
    ) -> Optional[ChatResponse]:
        """
        Get a cached response for a prompt if it exists.
        Returns None if no cache hit.
        """
        redis = await get_redis()
        if not redis:
            return None

        try:
            cache_key = self.cache_prefix + self.compute_prompt_hash(prompt, profile)
            cached_data = await redis.get(cache_key)
            
            if cached_data:
                logger.info(f"Prompt cache HIT for hash: {cache_key}")
                data = json.loads(cached_data)
                return ChatResponse(
                    type=data.get("type", "text"),
                    content=data.get("content", ""),
                    reasoning=data.get("reasoning", "Cached response"),
                )
            
            logger.debug(f"Prompt cache MISS for hash: {cache_key}")
            return None
            
        except Exception as e:
            logger.warning(f"Prompt cache read error: {e}")
            return None

    async def cache_response(
        self, prompt: str, profile: str, response: ChatResponse
    ) -> bool:
        """
        Cache an LLM response for future use.
        Returns True if successfully cached, False otherwise.
        """
        redis = await get_redis()
        if not redis:
            return False

        try:
            cache_key = self.cache_prefix + self.compute_prompt_hash(prompt, profile)
            
            # Serialize response
            data = {
                "type": response.type,
                "content": response.content,
                "reasoning": response.reasoning or "Cached response",
            }
            
            # Cache with TTL
            await redis.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(data)
            )
            
            logger.info(f"Cached LLM response with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.warning(f"Prompt cache write error: {e}")
            return False

    async def clear_cache(self, pattern: str = "*") -> int:
        """
        Clear cached prompts matching a pattern.
        Returns the number of keys deleted.
        """
        redis = await get_redis()
        if not redis:
            return 0

        try:
            full_pattern = self.cache_prefix + pattern
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await redis.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += await redis.delete(*keys)
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {deleted} cached prompts matching pattern: {pattern}")
            return deleted
            
        except Exception as e:
            logger.warning(f"Prompt cache clear error: {e}")
            return 0

