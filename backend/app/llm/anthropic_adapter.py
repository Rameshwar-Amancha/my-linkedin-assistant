"""
anthropic_adapter.py — Anthropic Claude provider adapter
"""

from __future__ import annotations

import logging

import httpx

from app.config.settings import get_settings
from app.llm.base import BaseLLMProvider, LLMProviderError, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"

    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMProviderError("anthropic", "ANTHROPIC_API_KEY is not configured.")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        system_content = ""
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        payload: dict = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }

        if system_content:
            payload["system"] = system_content

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.BASE_URL, headers=headers, json=payload)

            if response.status_code == 401:
                raise LLMProviderError("anthropic", "Invalid API key.", 401)
            if response.status_code == 429:
                raise LLMProviderError("anthropic", "Rate limit exceeded.", 429)
            if not response.is_success:
                detail = response.json().get("error", {}).get("message", response.text)
                raise LLMProviderError("anthropic", f"API error: {detail}", response.status_code)

            data = response.json()
            content_blocks = data.get("content", [])
            text = "".join(
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            ).strip()

            usage = data.get("usage", {})

            return LLMResponse(
                content=text,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                model=data.get("model", settings.ANTHROPIC_MODEL),
                provider="anthropic",
                finish_reason=data.get("stop_reason", ""),
            )

        except httpx.TimeoutException:
            raise LLMProviderError("anthropic", "Request timed out after 60 seconds.", 408)
        except httpx.RequestError as e:
            raise LLMProviderError("anthropic", f"Network error: {e}", 503)
