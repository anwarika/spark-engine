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
