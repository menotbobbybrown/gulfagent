from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""

    # Supabase
    supabase_url: str = ""           # postgres connection string (asyncpg)
    supabase_url_http: str = ""      # https://[ref].supabase.co  (for Storage/Auth SDK)
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # Evolution API (WhatsApp)
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    whatsapp_instance: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_basic: str = ""
    stripe_price_pro: str = ""

    # Ollama (Arabic fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # App
    next_public_supabase_url: str = ""
    next_public_supabase_anon_key: str = ""
    next_public_app_url: str = "http://localhost:3000"

    # Tier credit limits
    credits_basic: int = 5_000
    credits_pro: int = 20_000
    task_limit_basic: int = 50
    task_limit_pro: int = 200

    # T77 — Langfuse (optional, observability)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # T78 — Sentry (optional, error tracking)
    sentry_dsn: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
