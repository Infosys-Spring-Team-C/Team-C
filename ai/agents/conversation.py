from __future__ import annotations
import re
from typing import Any
from ai.schemas import ConversationSummary, ActionItem
from ai.providers import BaseLLMProvider
from ._base import structured_task


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 10]

def _summarize_single(request: dict[str, Any], provider: BaseLLMProvider) -> ConversationSummary:
    transcript = str(request.get("transcript", "")).strip()
    notes = str(request.get("notes", "")).strip()
    combined = "\n".join(x for x in [transcript, notes] if x)
    def mock() -> ConversationSummary:
        sents = _sentences(combined)
        def matching(words: tuple[str, ...]) -> list[str]:
            return [s for s in sents if any(w in s.lower() for w in words)][:5]
        pain = matching(("pain", "problem", "challenge", "slow", "manual", "difficult", "struggle"))
        objections = matching(("concern", "objection", "budget", "price", "expensive", "risk", "not sure"))
        requirements = matching(("need", "require", "must", "want", "looking for"))
        interests = matching(("interested", "feature", "integration", "demo", "product"))
        buying = matching(("timeline", "budget", "evaluate", "proposal", "purchase", "decision"))
        competitors = matching(("competitor", "alternative", "versus", "vs."))
        decisions = matching(("decided", "agree", "committed", "will move", "approved"))
        actions: list[ActionItem] = []
        for sent in matching(("will send", "will share", "will schedule", "will provide", "action item", "follow up")):
            owner = None
            m = re.match(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|to)", sent)
            if m: owner = m.group(1)
            date = None
            d = re.search(r"\b(?:by|on)\s+([A-Z][a-z]+\s+\d{1,2}(?:,?\s+\d{4})?|\d{4}-\d{2}-\d{2})", sent)
            if d: date = d.group(1)
            actions.append(ActionItem(action=sent, owner=owner, due_date=date, evidence=sent,
                                      confidence="high" if owner or date else "medium"))
        summary = " ".join(sents[:3]) if sents else "No analyzable transcript or notes were supplied."
        uncertain = []
        if not actions: uncertain.append("No explicit action item, owner, or due date was detected.")
        if not requirements: uncertain.append("No explicit customer requirement was detected.")
        return ConversationSummary(executive_summary=summary, key_discussion_points=sents[:6], customer_requirements=requirements,
            pain_points=pain, objections=objections, product_interests=interests, buying_signals=buying,
            competitor_mentions=competitors, decisions_and_commitments=decisions, action_items=actions,
            suggested_follow_up="Send a concise recap that distinguishes confirmed points from open questions, then ask for the next agreed step.",
            missing_or_uncertain=uncertain)
    return structured_task(provider, "conversation", {"transcript": transcript, "notes": notes}, ConversationSummary, mock)


def summarize_conversation(request: dict[str, Any], provider: BaseLLMProvider) -> ConversationSummary:
    """Chunk long transcripts, summarize each chunk, then synthesize the chunk summaries.

    This keeps model requests manageable while preserving the rule that every final point
    must originate in supplied transcript or note content.
    """
    transcript = str(request.get("transcript", "")).strip()
    notes = str(request.get("notes", "")).strip()
    chunk_size = 12000
    if len(transcript) <= chunk_size:
        return _summarize_single(request, provider)
    chunks = [transcript[i:i + chunk_size] for i in range(0, len(transcript), chunk_size)]
    partials = [_summarize_single({"transcript": chunk, "notes": ""}, provider) for chunk in chunks]
    synthesis_source = "\n".join(f"Chunk {i+1}: {item.executive_summary}" for i, item in enumerate(partials))
    final = _summarize_single({"transcript": synthesis_source, "notes": notes}, provider)
    final.source_note = (f"Hierarchical summary from {len(chunks)} supplied transcript chunks and supplied notes; "
                         "no facts were added outside those sources.")
    return final
