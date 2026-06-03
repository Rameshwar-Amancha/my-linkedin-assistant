"""
openai_adapter.py — OpenAI provider adapter
"""

from __future__ import annotations

import logging

import httpx

from app.config.settings import get_settings
from app.llm.base import BaseLLMProvider, LLMMessage, LLMProviderError, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise LLMProviderError("openai", "OPENAI_API_KEY is not configured.")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.BASE_URL, headers=headers, json=payload)

            if response.status_code == 401:
                raise LLMProviderError("openai", "Invalid API key.", 401)
            if response.status_code == 429:
                raise LLMProviderError("openai", "Rate limit exceeded. Please try again shortly.", 429)
            if not response.is_success:
                detail = response.json().get("error", {}).get("message", response.text)
                raise LLMProviderError("openai", f"API error: {detail}", response.status_code)

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"].strip(),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                model=data.get("model", settings.OPENAI_MODEL),
                provider="openai",
                finish_reason=choice.get("finish_reason", ""),
            )

        except httpx.TimeoutException:
            raise LLMProviderError("openai", "Request timed out after 60 seconds.", 408)
        except httpx.RequestError as e:
            raise LLMProviderError("openai", f"Network error: {e}", 503)
