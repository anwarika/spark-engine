from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str = ""
    redis_url: str = "redis://localhost:6379"
    
    # LLM Settings
    llm_provider: str = "openai"  # openai, anthropic, openrouter
    
    openai_api_key: Optional[str] = None
    openai_model: str = "o3-mini"
    
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-opus-20240229"
    
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o"
    
    environment: str = "development"
    log_level: str = "INFO"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    max_component_size_bytes: int = 51200
    max_bundle_size_bytes: int = 1048576
    compilation_timeout_seconds: int = 30
    cache_ttl_seconds: int = 3600
    rate_limit_requests_per_minute: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
