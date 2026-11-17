"""Provider-agnostic LLM client.

The AI/ML layer never talks to a vendor SDK directly: it calls this shim.  That
keeps three promises the Milestone reviews care about:
  1. the app boots and all endpoints work with **no** API key (heuristic mode),
  2. swapping providers is a one-file change,
  3. every call is timed, counted and logged for the reproducibility appendix.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class LLMUnavailable(RuntimeError):
    """Raised when no provider is configured or the call fails."""


@dataclass
class LLMResponse:
    text: str
    model: str
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Thin wrapper over a chat-completions endpoint with graceful degradation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str = OPENAI_URL,
        timeout: float = 45.0,
        max_retries: int = 2,
        enabled: bool | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.enabled = (bool(self.api_key) if enabled is None else enabled)
        self.calls = 0
        self.total_latency_ms = 0

    # -- capability check ---------------------------------------------------
    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key)

    # -- core call ----------------------------------------------------------
    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 900,
        json_mode: bool = False,
    ) -> LLMResponse:
        if not self.available:
            raise LLMUnavailable("No LLM provider configured (set OPENAI_API_KEY).")

        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                resp.raise_for_status()
                body = resp.json()
                latency = int((time.perf_counter() - started) * 1000)
                self.calls += 1
                self.total_latency_ms += latency
                usage = body.get("usage", {})
                return LLMResponse(
                    text=body["choices"][0]["message"]["content"],
                    model=body.get("model", self.model),
                    latency_ms=latency,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    raw=body,
                )
            except Exception as exc:  # noqa: BLE001 - retry any transport/HTTP error
                last_err = exc
                log.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, self.max_retries + 1, exc)
                time.sleep(0.6 * (attempt + 1))

        raise LLMUnavailable(f"LLM call failed after retries: {last_err}")

    # -- helpers ------------------------------------------------------------
    def chat_json(self, system: str, user: str, **kw: Any) -> tuple[dict[str, Any], LLMResponse]:
        resp = self.chat(system, user, json_mode=True, **kw)
        try:
            return json.loads(resp.text), resp
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"LLM returned invalid JSON: {exc}") from exc

    def stats(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "avg_latency_ms": round(self.total_latency_ms / self.calls, 1) if self.calls else 0,
            "model": self.model,
            "available": self.available,
        }


_default: LLMClient | None = None


def get_llm() -> LLMClient:
    """Process-wide singleton so token accounting is meaningful."""
    global _default
    if _default is None:
        _default = LLMClient()
    return _default
