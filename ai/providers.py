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


class RetryableProviderError(ProviderError):
    """A transient failure (timeout, rate limit, 5xx) that is safe to retry."""


#: HTTP statuses where a retry can succeed without changing the request.
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

#: Exception class-name fragments that indicate a transient transport failure.
_RETRYABLE_NAMES = (
    "timeout",
    "timedout",
    "ratelimit",
    "connection",
    "temporarilyunavailable",
    "internalservererror",
    "serviceunavailable",
    "overloaded",
)


def _status_code(exc: BaseException) -> int | None:
    """Best-effort HTTP status extraction across the provider SDKs."""
    for attribute in ("status_code", "http_status", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def is_retryable(exc: BaseException) -> bool:
    """Return ``True`` only for failures that a retry can plausibly fix.

    Authentication, permission, bad-request, schema-validation and JSON-decoding
    failures are deterministic: retrying them wastes quota and hides the real
    error behind a generic message.
    """
    if isinstance(exc, RetryableProviderError):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = _status_code(exc)
    if status is not None:
        return status in _RETRYABLE_STATUS
    name = type(exc).__name__.lower()
    return any(token in name for token in _RETRYABLE_NAMES)


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
        attempts = max(0, self.settings.request_retries) + 1
        for attempt in range(attempts):
            try:
                raw = self._json_response(system, user)
                return response_model.model_validate(raw)
            except Exception as exc:
                last_error = exc
                if not is_retryable(exc) or attempt == attempts - 1:
                    break
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


class GroqProvider(BaseLLMProvider):
    """Groq's OpenAI-compatible endpoint (JSON mode, open-weight models)."""

    name = "groq"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.groq_api_key:
            raise ProviderError("GROQ_API_KEY is not configured. Enable demo mode or configure a provider key.")
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                timeout=settings.request_timeout_seconds,
            )
        except ImportError as exc:
            raise ProviderError("Install the optional 'openai' package to use the Groq provider.") from exc

    def _json_response(self, system: str, user: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)


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
            self.client = genai.Client(
                api_key=settings.google_api_key,
                # The SDK takes milliseconds; without this Gemini had no timeout.
                http_options={"timeout": max(1000, int(settings.request_timeout_seconds * 1000))},
            )
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
    if settings.llm_provider == "groq":
        return GroqProvider(settings)
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings)
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    raise ProviderError(f"Unsupported LLM provider '{settings.llm_provider}'. Use mock, groq, openai, or gemini.")
