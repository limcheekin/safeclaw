from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # Cerbos
    CERBOS_BASE_URL: str = "http://cerbos:3592"
    CERBOS_TIMEOUT_MS: int = 500
    CERBOS_CACHE_TTL_HIGH: int = 30
    CERBOS_CACHE_TTL_MED: int = 60
    CERBOS_CACHE_TTL_LOW: int = 300
    CERBOS_CACHE_BACKEND: str = "redis://redis:6379/0"
    CERBOS_CIRCUIT_BREAKER_FAILURES: int = 5

    # Principal Enrichment
    PRINCIPAL_ATTR_SOURCE: Literal["jwt", "introspect", "user_service"] = "jwt"
    JWT_PUBLIC_KEY: str | None = None
    USER_SERVICE_URL: str | None = None
    AUTH_FALLBACK_MODE: Literal["deny", "allow_with_logs"] = "deny"

    # Redis (General use if needed, but Cerbos has its own config above)
    REDIS_URL: str = "redis://redis:6379/0"

    # MCP Server
    MCP_SERVER_NAME: str = "safeclaw-mcp"
    MCP_SERVER_PORT: int = 8000


settings = Settings()
