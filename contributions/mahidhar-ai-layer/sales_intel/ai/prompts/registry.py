"""Versioned prompt registry.

Day 14 of the schedule is "tune prompts and scoring weights" — that only works
if prompts are addressable, diff-able artefacts rather than f-strings buried in
services. Each template carries an id, a version and metadata so the tuner can
A/B them and the tuning report can cite exactly what shipped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    system: str
    user: str
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> tuple[str, str]:
        """Return (system, user) with every placeholder filled.

        Missing keys raise a KeyError with the offending name, which is far
        friendlier than a half-rendered prompt reaching production.
        """
        try:
            return self.system.format(**kwargs), self.user.format(**kwargs)
        except KeyError as exc:
            raise KeyError(f"prompt '{self.id}' missing placeholder {exc}") from exc


# ---------------------------------------------------------------------------
# Outreach generation (Module 3) — three variants the Day-14 tuner compares.
# ---------------------------------------------------------------------------
OUTREACH_V1 = PromptTemplate(
    id="outreach_email",
    version="v1",
    description="Baseline: generic benefit-led email.",
    tags=["outreach", "baseline"],
    system=(
        "You are a B2B sales copywriter. Write concise, professional outreach emails. "
        "Never invent facts about the prospect."
    ),
    user=(
        "Write a {length} {tone} {email_type} email to {company} ({industry}).\n"
        "Goal: {goal}\nPain points: {pain_points}\n"
        "Return strict JSON with keys: subject, body, personalisation_notes."
    ),
)

OUTREACH_V2 = PromptTemplate(
    id="outreach_email",
    version="v2",
    description="PAS framework (Problem-Agitate-Solve) with one proof point.",
    tags=["outreach", "pas"],
    system=(
        "You are a senior B2B SDR writing cold outreach that gets replies. "
        "Use the Problem-Agitate-Solve structure. One proof point maximum. "
        "No flattery, no 'I hope this finds you well', no invented metrics."
    ),
    user=(
        "<prospect>\ncompany={company}\nindustry={industry}\npersona={persona}\n"
        "pain_points={pain_points}\n</prospect>\n"
        "<constraints>\ntone={tone}\nlength={length}\nemail_type={email_type}\n"
        "goal={goal}\n</constraints>\n"
        "Rules:\n"
        "- Subject line <= 60 chars, specific, no clickbait.\n"
        "- Body <= 120 words for 'short', <= 200 for 'long'.\n"
        "- Exactly one clear call-to-action question at the end.\n"
        "- Reference at least one named pain point verbatim.\n"
        "Return strict JSON: subject, body, call_to_action, personalisation_notes."
    ),
)

OUTREACH_V3 = PromptTemplate(
    id="outreach_email",
    version="v3",
    description="Insight-led hook + explicit CTA + role-aware framing.",
    tags=["outreach", "insight-led", "role_aware"],
    system=(
        "You write pattern-interrupt B2B outreach. You open with a specific, "
        "verifiable observation about the prospect's industry, then connect it to "
        "the sender's offer. You are concise, concrete and never hype."
    ),
    user=(
        "Prospect: {company} | Industry: {industry} | Persona: {persona}\n"
        "Pain points to acknowledge: {pain_points}\n"
        "Outreach goal: {goal} | Type: {email_type} | Tone: {tone} | Length: {length}\n"
        "Follow this skeleton:\n"
        "1) Hook: one sentence insight tied to their industry pain point.\n"
        "2) Relevance: one sentence on why it matters to their role now.\n"
        "3) Value: one sentence on the outcome we deliver (no metrics we cannot prove).\n"
        "4) CTA: a single low-friction question.\n"
        "Keep it under 150 words. Return strict JSON: subject, body, call_to_action, "
        "personalisation_notes."
    ),
)

OUTREACH_VARIANTS: dict[str, PromptTemplate] = {
    OUTREACH_V1.version: OUTREACH_V1,
    OUTREACH_V2.version: OUTREACH_V2,
    OUTREACH_V3.version: OUTREACH_V3,
}

# ---------------------------------------------------------------------------
# Conversation summarisation (Module 5) — Day 24.
# ---------------------------------------------------------------------------
SUMMARY_V1 = PromptTemplate(
    id="meeting_summary",
    version="v1",
    description="Baseline summariser: bullets + action items.",
    tags=["summary", "baseline"],
    system=(
        "You summarise B2B sales conversations. Be factual. Only report what is "
        "explicitly stated in the transcript."
    ),
    user=(
        "Summarise this sales conversation.\n\n{transcript}\n\n"
        "Return strict JSON with keys: summary, key_discussion_points, action_items, "
        "decisions, objections, next_step."
    ),
)

SUMMARY_V2 = PromptTemplate(
    id="meeting_summary",
    version="v2",
    description="Structured extraction with owner attribution and strict JSON schema.",
    tags=["summary", "structured", "owners"],
    system=(
        "You are a sales-operations analyst. You convert raw call transcripts into "
        "CRM-ready structured notes.\n"
        "HARD RULES:\n"
        "- Never invent an owner, date or commitment that is not in the transcript.\n"
        "- If a field is unknown use null (deliverables) or 'unassigned' (owner).\n"
        "- Attribute every action item to the person who actually accepted it.\n"
        "- Ignore small talk and internal asides unless they change the deal."
    ),
    user=(
        "Meeting metadata:\n"
        "- Interaction id: {interaction_id}\n"
        "- Meeting date: {meeting_date}\n"
        "- Known internal speakers: {internal_speakers}\n\n"
        "<transcript>\n{transcript}\n</transcript>\n\n"
        "Return strict JSON matching:\n"
        "{{\n"
        '  "summary": "<=80 word executive summary",\n'
        '  "key_discussion_points": [{{"topic": "", "detail": "", "sentiment": '
        '"positive|neutral|negative", "quote": ""}}],\n'
        '  "action_items": [{{"task": "", "owner": "", "owner_side": '
        '"internal|customer|unassigned", "due_hint": "", "priority": '
        '"high|medium|low", "source_quote": ""}}],\n'
        '  "decisions": [], "objections": [], "competitors_mentioned": [],\n'
        '  "next_step": "", "overall_sentiment": "positive|neutral|negative"\n'
        "}}\n"
        "Max {max_bullets} discussion points, max {max_action_items} action items."
    ),
)

SUMMARY_VARIANTS: dict[str, PromptTemplate] = {
    SUMMARY_V1.version: SUMMARY_V1,
    SUMMARY_V2.version: SUMMARY_V2,
}

DEFAULT_OUTREACH = OUTREACH_V2
DEFAULT_SUMMARY = SUMMARY_V2


def get_prompt(prompt_id: str, variant: str) -> PromptTemplate:
    registry = {
        "outreach_email": OUTREACH_VARIANTS,
        "meeting_summary": SUMMARY_VARIANTS,
    }
    try:
        return registry[prompt_id][variant]
    except KeyError as exc:
        raise KeyError(
            f"unknown prompt '{prompt_id}' variant '{variant}'; "
            f"available: {sorted(registry.get(prompt_id, {}))}"
        ) from exc


def catalogue() -> list[dict[str, str]]:
    """Machine-readable list — the API exposes this so the UI can show what ran."""
    return [
        {"id": p.id, "version": p.version, "description": p.description, "tags": p.tags}
        for p in [*OUTREACH_VARIANTS.values(), *SUMMARY_VARIANTS.values()]
    ]
