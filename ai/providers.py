"""LLM provider boundary with deterministic mock implementation and safe JSON validation."""
from __future__ import annotations
from abc import ABC, abstractmethod
import json
import time
from typing import Any, Callable, TypeVar
from pydantic import BaseModel
from utils.config import Settings
from utils.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    pass


class BaseLLMProvider(ABC):
    name = "base"
    is_mock = False

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def _json_response(self, system: str, user: str) -> dict[str, Any]:
        raise NotImplementedError

    def structured(
        self, system: str, user: str, response_model: type[T], fallback: Callable[[], T] | None = None
    ) -> T:
        """Call provider, retry transient errors, and validate before returning to UI."""
        last_error: Exception | None = None
        for attempt in range(self.settings.request_retries + 1):
            try:
                raw = self._json_response(system, user)
                return response_model.model_validate(raw)
            except Exception as exc:
                last_error = exc
                if attempt < self.settings.request_retries:
                    time.sleep(min(0.5 * (2**attempt), 2.0))
        # A production provider failure must remain visible. Returning deterministic content here
        # would blur mock output with real-model output and could mislead users.
        raise ProviderError(f"{self.name} could not produce a valid structured response: {last_error}") from last_error


class MockLLMProvider(BaseLLMProvider):
    """Does not call an external model. Agent-specific deterministic factories supply output."""
    name = "mock"
    is_mock = True

    def _json_response(self, system: str, user: str) -> dict[str, Any]:
        raise ProviderError("Mock provider requires the deterministic agent fallback.")

    def structured(self, system: str, user: str, response_model: type[T], fallback: Callable[[], T] | None = None) -> T:
        if fallback is None:
            raise ProviderError("No deterministic mock output is registered for this task.")
        return fallback()


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is not configured. Enable demo mode or configure a provider key.")
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.request_timeout_seconds)
        except ImportError as exc:
            raise ProviderError("Install the optional 'openai' package to use the OpenAI provider.") from exc

    def _json_response(self, system: str, user: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.google_api_key:
            raise ProviderError("GOOGLE_API_KEY is not configured. Enable demo mode or configure a provider key.")
        try:
            from google import genai
            self.client = genai.Client(api_key=settings.google_api_key)
            self._types = __import__("google.genai.types", fromlist=["GenerateContentConfig"])
        except ImportError as exc:
            raise ProviderError("Install the optional 'google-genai' package to use Gemini.") from exc

    def _json_response(self, system: str, user: str) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.settings.llm_model,
            contents=user,
            config=self._types.GenerateContentConfig(
                system_instruction=system,
                temperature=self.settings.llm_temperature,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text or "{}")


def create_provider(settings: Settings) -> BaseLLMProvider:
    if settings.demo_mode or settings.llm_provider == "mock":
        return MockLLMProvider(settings)
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings)
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    raise ProviderError(f"Unsupported LLM provider '{settings.llm_provider}'. Use mock, openai, or gemini.")
