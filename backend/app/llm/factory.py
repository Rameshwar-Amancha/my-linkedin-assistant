"""
factory.py — LLM provider factory

Returns the configured provider instance based on the LLM_PROVIDER setting.
Cached at module level for connection reuse.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config.settings import get_settings
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function — returns the active LLM provider based on settings.

    Cached so adapters aren't re-instantiated per request.
    """
    settings = get_settings()
    provider_name = settings.LLM_PROVIDER

    if provider_name == "openai":
        from app.llm.openai_adapter import OpenAIProvider
        logger.info("LLM provider: OpenAI (%s)", settings.OPENAI_MODEL)
        return OpenAIProvider()

    elif provider_name == "gemini":
        from app.llm.gemini_adapter import GeminiProvider
        logger.info("LLM provider: Google Gemini (%s)", settings.GEMINI_MODEL)
        return GeminiProvider()

    elif provider_name == "anthropic":
        from app.llm.anthropic_adapter import AnthropicProvider
        logger.info("LLM provider: Anthropic (%s)", settings.ANTHROPIC_MODEL)
        return AnthropicProvider()

    else:
        raise ValueError(f"Unsupported LLM provider: '{provider_name}'")
