from __future__ import annotations
from typing import Any, Callable, TypeVar
from pydantic import BaseModel
from ai.prompts import build_prompt
from ai.providers import BaseLLMProvider
T = TypeVar("T", bound=BaseModel)

def structured_task(provider: BaseLLMProvider, task: str, context: dict[str, Any], model: type[T], fallback: Callable[[], T]) -> T:
    system, user = build_prompt(task, context, model)
    return provider.structured(system, user, model, fallback=fallback)

def provided_fact(text: str, label: str, confidence: str = "medium") -> dict[str, Any]:
    return {"statement": f"{label}: {text}", "source": "User-provided context", "source_type": "provided", "confidence": confidence}
