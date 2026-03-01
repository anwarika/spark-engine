from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database Mode: 'supabase' or 'postgres'
    database_mode: str = "postgres"
    
    # Postgres Config
    database_url: str = "postgresql://postgres:password@localhost:5432/spark"
    
    # Supabase Config
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    
    redis_url: str = "redis://localhost:6379"
    
    # LLM Gateway Settings
    llm_provider: str = "openai"  # openai | openrouter | litellm | llmgw | custom
    llm_model: str = "gpt-4o-mini"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    # Fallback
    llm_fallback_provider: Optional[str] = None
    llm_fallback_model: Optional[str] = None
    llm_fallback_api_key: Optional[str] = None
    llm_fallback_base_url: Optional[str] = None
    # Provider-specific (alternative to llm_api_key)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: str = "spark-engine"
    litellm_api_key: Optional[str] = None
    llmgw_api_key: Optional[str] = None
    llmgw_base_url: Optional[str] = None
    custom_llm_api_key: Optional[str] = None
    custom_llm_base_url: Optional[str] = None
    
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
