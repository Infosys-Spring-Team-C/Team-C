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

_HONORIFICS = {"dr", "mr", "mrs", "ms", "prof", "sir", "madam"}

def contact_first_name(contact: str, default: str = "there") -> str:
    """Return the greeting name, skipping titles such as ``Dr.`` or ``Prof.``.

    ``"Dr. Sofia Alvarez".split()[0]`` yields ``"Dr."`` and produced
    ``"Hi Dr.,"`` in generated drafts.  Strip leading honorifics so the
    greeting addresses the person, not the title.
    """
    words = [word.strip(",;:") for word in str(contact or "").replace(",", " ").split()]
    for word in words:
        if word and word.lower().rstrip(".") not in _HONORIFICS:
            return word
    return default
