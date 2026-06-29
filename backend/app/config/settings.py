"""
settings.py — Centralised configuration management using Pydantic v2 Settings.

All secrets loaded from environment variables / .env file.
Never hardcode secrets in source code.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve .env relative to this file (backend/.env), regardless of
# the working directory uvicorn / pytest are launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Server
    # -----------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # -----------------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------------
    API_SECRET_KEY: str
    ALLOWED_ORIGINS: Any = ["chrome-extension://*", "http://localhost:3000"]
    # NOTE: chrome-extension://* is parsed by main.py's CORS logic to use
    #       allow_origin_regex instead of allow_origins, because Starlette
    #       does not support wildcards in allow_origins values.
    #       You can also list specific extension IDs, which will be matched
    #       exactly (faster) — but * is the simplest for development.

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./lea_data.db"

    # -----------------------------------------------------------------------
    # LLM Provider
    # -----------------------------------------------------------------------
    LLM_PROVIDER: str = "openai"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 1024
    OPENAI_TEMPERATURE: float = 0.7

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # -----------------------------------------------------------------------
    # Caching
    # -----------------------------------------------------------------------
    REDIS_URL: str = ""
    TRENDS_CACHE_TTL_SECONDS: int = 1800
    REPLY_CACHE_TTL_SECONDS: int = 0

    # -----------------------------------------------------------------------
    # Webhooks
    # -----------------------------------------------------------------------
    WEBHOOK_SIGNING_SECRET: str = ""

    # -----------------------------------------------------------------------
    # Scraping / Trends
    # -----------------------------------------------------------------------
    NEWS_API_KEY: str = ""
    HN_FETCH_LIMIT: int = 30
    REDDIT_USER_AGENT: str = "LEA-TrendBot/1.0 (educational tool)"
    SCRAPING_REQUEST_TIMEOUT_SECONDS: int = 15
    SCRAPING_MAX_RETRIES: int = 3

    # -----------------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------------
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        import json

        if isinstance(v, list):
            result = []
            for item in v:
                s = str(item).strip()
                if not s:
                    continue
                if s.startswith("["):
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, list):
                            for sub in parsed:
                                sub_s = str(sub).strip()
                                if sub_s:
                                    result.extend(
                                        origin.strip()
                                        for origin in sub_s.split(",")
                                        if origin.strip()
                                    )
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                result.extend(
                    origin.strip() for origin in s.split(",") if origin.strip()
                )
            return result
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except (json.JSONDecodeError, TypeError):
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return upper

    @model_validator(mode="after")
    def validate_llm_keys(self) -> "Settings":
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        if self.LLM_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        if self.LLM_PROVIDER == "anthropic" and not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance. Loaded once at startup."""
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(name)s (%(funcName)s:%(lineno)d) — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    return settings
