"""
gemini_adapter.py — Google Gemini provider adapter
"""

from __future__ import annotations

import logging

import httpx

from app.config.settings import get_settings
from app.llm.base import BaseLLMProvider, LLMProviderError, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMProviderError("gemini", "GEMINI_API_KEY is not configured.")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        url = self.BASE_URL.format(model=settings.GEMINI_MODEL)
        params = {"key": settings.GEMINI_API_KEY}

        # Gemini uses a different message structure
        # System prompt goes into systemInstruction, user messages in contents
        system_content = ""
        user_parts = []

        for msg in request.messages:
            if msg.role == "system":
                system_content = msg.content
            elif msg.role == "user":
                user_parts.append({"text": msg.content})
            elif msg.role == "assistant":
                # Gemini uses "model" role for assistant turns
                user_parts.append({"role": "model", "parts": [{"text": msg.content}]})

        payload: dict = {
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        if system_content:
            payload["systemInstruction"] = {"parts": [{"text": system_content}]}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, params=params, json=payload)

            if response.status_code == 400:
                detail = response.json().get("error", {}).get("message", "Bad request")
                raise LLMProviderError("gemini", f"Bad request: {detail}", 400)
            if response.status_code == 403:
                raise LLMProviderError("gemini", "Invalid API key.", 403)
            if response.status_code == 429:
                raise LLMProviderError("gemini", "Rate limit exceeded.", 429)
            if not response.is_success:
                raise LLMProviderError("gemini", f"API error: {response.status_code}", response.status_code)

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError("gemini", "No candidates returned from Gemini.")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()

            usage = data.get("usageMetadata", {})

            return LLMResponse(
                content=text,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
                model=settings.GEMINI_MODEL,
                provider="gemini",
                finish_reason=candidates[0].get("finishReason", ""),
            )

        except httpx.TimeoutException:
            raise LLMProviderError("gemini", "Request timed out after 60 seconds.", 408)
        except httpx.RequestError as e:
            raise LLMProviderError("gemini", f"Network error: {e}", 503)
