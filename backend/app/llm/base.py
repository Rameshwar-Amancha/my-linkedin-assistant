"""
base.py — Abstract LLM provider interface

All provider adapters implement this interface, enabling transparent
switching between OpenAI, Gemini, and Anthropic without changing service code.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMRequest:
    """Structured LLM generation request."""
    messages: list[LLMMessage]
    max_tokens: int = 1024
    temperature: float = 0.7
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class LLMResponse:
    """Structured LLM generation response."""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    finish_reason: str = ""

    @property
    def success(self) -> bool:
        return bool(self.content and self.content.strip())


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM provider adapters.

    Implementations must be async and handle their own retry logic.
    Token tracking is mandatory — used for observability and cost monitoring.
    """

    provider_name: str = "base"

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a completion for the given request.

        Args:
            request: Structured LLM request with messages and parameters

        Returns:
            LLMResponse with content and token usage

        Raises:
            LLMProviderError: On authentication, rate limit, or network errors
        """
        ...

    async def generate_with_timing(self, request: LLMRequest) -> LLMResponse:
        """Wrapper that adds latency tracking."""
        start = time.perf_counter()
        response = await self.generate(request)
        response.latency_ms = int((time.perf_counter() - start) * 1000)
        return response

    def build_messages(
        self, system_prompt: str, user_content: str
    ) -> list[LLMMessage]:
        """Helper to construct standard system + user message list."""
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]


class LLMProviderError(Exception):
    """Raised when an LLM provider returns an error or is unavailable."""

    def __init__(self, provider: str, message: str, status_code: int = 500):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")
