"""Day 24 — meeting / call summarisation (Module 5).

Pipeline (LangGraph-shaped, but dependency-free):

    normalise -> segment -> (LLM extraction | heuristic extraction)
              -> validate/repair -> enrich (dates, owners, talk ratio)
              -> ConversationSummary

Two engines:
  * **llm**      — prompt SUMMARY_V2, strict-JSON extraction, schema-validated,
                   any malformed item is dropped rather than allowed to poison
                   the CRM payload.
  * **heuristic** — rule-based fallback so summarisation always works: CI needs
                   no network call and a provider outage cannot blank a CRM record.

The heuristic engine is not a toy: it does real sentence scoring (cue phrases,
commitment verbs, owner detection, relative-date parsing), which is exactly what
keeps the endpoint under the 5-second performance target from Day 34.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from sales_intel.ai.llm.client import LLMClient, LLMUnavailable, get_llm
from sales_intel.ai.prompts.registry import DEFAULT_SUMMARY, get_prompt
from sales_intel.config import SUMMARY_CONFIG
from sales_intel.schemas import (
    ActionItem,
    ConversationSummary,
    DiscussionPoint,
    Utterance,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cue lexicons (kept as data, not code, so the Day-27 quality review can edit)
# ---------------------------------------------------------------------------
COMMITMENT_CUES = (
    "i will", "i'll", "we will", "we'll", "you'll", "you will", "let me", "let's",
    "we should", "i can", "we can", "please send", "send me", "share the",
    "send over", "follow up", "circle back", "set up", "schedule", "book",
    "prepare", "put together", "connect you", "intro you", "need to", "has to",
    "next step", "action item", "i'll take", "we'll take",
)
DECISION_CUES = (
    "we decided", "decision is", "we've decided", "agreed", "we're going with",
    "let's go with", "final answer", "we will proceed", "approved", "signed off",
    "locked in", "we're moving forward", "confirmed",
)
OBJECTION_CUES = (
    "concern", "worried", "too expensive", "too costly", "budget is", "not sure",
    "pushback", "risk", "hesitant", "problem is", "issue is", "but we", "however",
    "doesn't support", "missing", "gap", "competitor is cheaper", "too early",
)
NEXT_STEP_CUES = (
    "next step", "next time", "in our next", "we'll follow up", "i'll follow up",
    "let's plan", "before we", "by next", "send invite", "share the invite",
)
POSITIVE_CUES = (
    "great", "perfect", "excellent", "exactly", "love", "sounds good", "makes sense",
    "impressive", "helpful", "definitely", "absolutely", "happy to", "agree",
)
NEGATIVE_CUES = (
    "concern", "worried", "problem", "issue", "expensive", "delay", "risk",
    "unfortunately", "not happy", "too early", "difficult", "missing", "fail",
)

# Seller-side vs buyer-side language, used to infer who is "internal" when the
# transcript carries no speaker metadata (the common case for pasted transcripts).
SELLER_CUES = (
    "i'll send", "i will send", "let me", "we'll prepare", "we will prepare",
    "i'll prepare", "i can send", "we can offer", "our platform", "our team can",
    "happy to", "let's schedule", "i'll put together", "i can put together",
    "we'll set up", "we will set up", "i'll share", "we'll show", "i'll follow up",
    "i'll take care", "we'll book", "our product", "our solution", "i can put",
)
BUYER_CUES = (
    "we need", "we currently", "we're evaluating", "we are evaluating", "our budget",
    "our ciso", "our legal", "our team is", "i need to check", "send me",
    "send it to me", "can you send", "please share", "please send", "how does this compare",
    "your pricing", "what does it cost", "our side", "i will take it to",
)

COMPETITOR_NAMES = (
    "salesforce", "hubspot", "pipedrive", "zoho", "dynamics", "freshsales",
    "outreach.io", "salesloft", "apollo", "clari", "gong", "6sense",
    "marketo", "intercom", "clay", "instantly", "lemlist",
)

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6,
}
RELATIVE_DAYS = {
    "today": 0, "tonight": 0, "tomorrow": 1, "day after tomorrow": 2,
    "next week": 7, "next monday": None, "end of week": None,
    "this week": 0, "next month": 30, "in a week": 7, "in two weeks": 14,
    "in a month": 30, "by friday": None,
}
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Meta / retrospective statements that look like commitments but are not actions.
META_PREFIXES = (
    "we wanted to", "i wanted to", "thanks", "thank you", "as discussed", "as agreed",
    "just to confirm", "just checking", "appreciate", "nice to meet", "good to see",
    "to recap", "to summarise", "to summarize", "we discussed", "we talked",
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
NAME_TOKEN = re.compile(r"\b([A-Z][a-z]{1,15})\b")
TIME_TOKEN = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s?(am|pm)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    text = re.sub(r"\[(\d{1,2}:)?\d{1,2}:\d{2}(:\d{2})?\]", " ", text)  # [00:12:33]
    text = re.sub(r"\b(um|uh|erm|like,|you know,)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if len(s.strip()) > 2]


def infer_internal_speakers(utterances: list[Utterance]) -> set[str]:
    """Best-effort detection of the selling team when no metadata is supplied.

    Scores each speaker on seller-side vs buyer-side language. Falls back to the
    first speaker (call transcripts conventionally open with the rep).
    """
    scores: dict[str, int] = {}
    for u in utterances:
        text = u.text.lower()
        seller = sum(1 for c in SELLER_CUES if c in text)
        buyer = sum(1 for c in BUYER_CUES if c in text)
        scores[u.speaker] = scores.get(u.speaker, 0) + seller - buyer
    inferred = {spk.lower() for spk, sc in scores.items() if sc > 0}
    if not inferred and utterances:
        inferred = {utterances[0].speaker.lower()}
    # Guard: never mark the whole call internal (that would break side attribution).
    if utterances and len(inferred) >= len({u.speaker for u in utterances}):
        inferred = {utterances[0].speaker.lower()}
    return inferred


def _internal_speakers(
    utterances: Iterable[Utterance], declared: set[str] | None = None
) -> set[str]:
    items = list(utterances)
    declared = {d.lower() for d in (declared or set())}
    flagged = {u.speaker.lower() for u in items if u.is_internal}
    explicit = declared | flagged
    if explicit:
        return explicit
    return infer_internal_speakers(items)


# ---------------------------------------------------------------------------
# Date / owner parsing
# ---------------------------------------------------------------------------
def parse_due_date(hint: str | None, meeting_date: date) -> date | None:
    """Turn a natural-language due hint into a concrete date.

    Handles: 'tomorrow', 'today', 'in two weeks', 'by Friday', 'next Monday',
    'on 12 Nov', '12/11', 'before end of week', 'next month'.
    Returns None when the hint carries no usable date.
    """
    if not hint:
        return None
    h = hint.lower().strip()

    m = re.search(r"\bin (\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|week|month)s?\b", h)
    if m:
        n_raw, unit = m.groups()
        n = int(n_raw) if n_raw.isdigit() else NUMBER_WORDS.get(n_raw, 1)
        return meeting_date + timedelta(days=n * {"day": 1, "week": 7, "month": 30}[unit])

    for phrase, offset in RELATIVE_DAYS.items():
        if phrase in h and offset is not None:
            return meeting_date + timedelta(days=offset)

    if "end of week" in h or "by friday" in h:
        days = (4 - meeting_date.weekday()) % 7
        return meeting_date + timedelta(days=days)

    for name, idx in WEEKDAYS.items():
        if name in h:
            days = (idx - meeting_date.weekday()) % 7 or 7
            if "next" in h:
                days = days if days >= 7 else days + 7
            return meeting_date + timedelta(days=days)

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", h)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else meeting_date.year
        if yr < 100:
            yr += 2000
        try:
            return date(yr, mo, d)
        except ValueError:
            return None

    m = re.search(r"\b(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", h)
    if m:
        months = ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
        try:
            return date(meeting_date.year, months.index(m.group(2)) + 1, int(m.group(1)))
        except ValueError:
            return None
    return None


def _detect_owner(
    sentence: str, speaker: str, internal: set[str], all_speakers: set[str]
) -> tuple[str, str]:
    """Resolve who owns the action. Returns (owner, owner_side)."""
    s = sentence.lower()
    speaker_internal = speaker.lower() in internal

    # "I'll ..." -> the speaker owns it.
    if re.search(
        r"\b(i will|i'll|let me|i can|i'll take|i will take|i need to|i have to|"
        r"i should|i am going to|i'm going to|i want to)\b", s
    ):
        return speaker, "internal" if speaker_internal else "customer"
    # "you'll ..." addressed to the other party.
    if re.search(r"\b(you will|you'll|can you|could you|please send|please share)\b", s):
        for sp in all_speakers:
            if sp != speaker:
                return sp, "internal" if sp.lower() in internal else "customer"
    # "we'll ..." -> the speaker's side.
    if re.search(r"\b(we will|we'll|we should|we can|let's|let us)\b", s):
        return speaker, "internal" if speaker_internal else "customer"
    # Explicit name mention: "Ravi will send ..."
    for sp in all_speakers:
        if sp.split()[0].lower() in s:
            return sp, "internal" if sp.lower() in internal else "customer"
    return "unassigned", "unassigned"


def _priority_for(sentence: str, has_date: bool) -> str:
    s = sentence.lower()
    if any(k in s for k in ("asap", "urgent", "today", "tomorrow", "by friday", "critical", "blocker")):
        return "high"
    if has_date or any(k in s for k in ("next week", "before we", "needed for")):
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Heuristic engine
# ---------------------------------------------------------------------------
def _sentiment(sentence: str) -> str:
    s = sentence.lower()
    pos = sum(1 for c in POSITIVE_CUES if c in s)
    neg = sum(1 for c in NEGATIVE_CUES if c in s)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _score_sentence(sentence: str) -> float:
    """Rank sentences by informational value (used for summary + key points)."""
    s = sentence.lower()
    score = min(len(sentence) / 220.0, 1.0) * 1.5
    score += 2.0 * sum(1 for c in COMMITMENT_CUES if c in s)
    score += 2.5 * sum(1 for c in DECISION_CUES if c in s)
    score += 1.5 * sum(1 for c in OBJECTION_CUES if c in s)
    score += 2.0 * sum(1 for c in NEXT_STEP_CUES if c in s)
    if re.search(r"\d", s):
        score += 0.8
    if re.search(r"\$|₹|€|usd|inr|budget", s):
        score += 1.0
    return score


def _topic_of(sentence: str) -> str:
    """Map a sentence to a CRM-friendly topic bucket.

    Ordered most-specific first; `integration` precedes `competition` so
    "does your API sync with HubSpot?" is filed as an integration question
    rather than a competitive threat.
    """
    s = sentence.lower()
    topics: list[tuple[str, tuple[str, ...]]] = [
        ("security", ("security", "compliance", "gdpr", "soc 2", "soc2", "privacy",
                      "data residency", "data protection", "dpa", "retention", "ciso",
                      "legal", "dpo", "audit")),
        ("business case", ("roi", "business case", "finance", "justification",
                           "cost saving", "payback", "approval")),
        ("pricing", ("price", "pricing", "cost", "budget", "quote", "discount",
                     "inr", "usd", "per seat", "tier")),
        ("demo", ("demo", "walkthrough", "poc", "trial", "sandbox", "pilot results")),
        ("integration", ("integration", "api", "crm", "sync", "import", "two-way",
                         "webhook", "field mapping")),
        ("expansion", ("expansion", "upsell", "renewal", "renew", "more seats",
                       "additional seats", "adoption", "roll out", "rollout")),
        ("competition", tuple(COMPETITOR_NAMES) + ("competitor", "alternative", "vendor",
                                                   "compared to", "instead of")),
        ("product", ("dashboard", "visibility", "reporting", "kanban", "pipeline view",
                     "workflow", "scoring")),
        ("scope", ("scope", "module", "feature", "requirement", "customisation",
                   "customization", "onboarding")),
        ("timeline", ("timeline", "deadline", "schedule", "q1", "q2", "q3", "q4",
                      "next week", "next month", "next quarter", "go-live", "go live",
                      "january", "february", "march", "april", "may", "june", "july",
                      "august", "september", "october", "november", "december")),
        ("next steps", ("next step", "follow up", "action item", "todo", "to-do",
                        "agree next")),
    ]
    for topic, keys in topics:
        if any(k in s for k in keys):
            return topic
    return "general"


def heuristic_summarise(
    utterances: list[Utterance],
    interaction_id: str,
    lead_id: str | None = None,
    meeting_date: date | None = None,
    internal_speakers: set[str] | None = None,
) -> ConversationSummary:
    meeting_date = meeting_date or date.today()
    internal = _internal_speakers(utterances, internal_speakers)
    all_speakers = {u.speaker for u in utterances if u.speaker}

    # 1) flatten to (speaker, sentence) with cleaned text
    flat: list[tuple[str, str]] = []
    for u in utterances:
        for sent in _sentences(_clean(u.text)):
            flat.append((u.speaker, sent))

    if not flat:
        return ConversationSummary(
            interaction_id=interaction_id,
            lead_id=lead_id,
            summary="No usable transcript content was provided.",
            key_discussion_points=[],
            action_items=[],
            confidence=0.0,
            engine="heuristic",
            model="rules-v1",
        )

    # 2) rank sentences once; reuse for summary, points and action extraction
    ranked = sorted(flat, key=lambda sp: _score_sentence(sp[1]), reverse=True)

    # 3) action items
    actions: list[ActionItem] = []
    seen_tasks: set[str] = set()
    action_tokens: list[set[str]] = []
    for speaker, sent in ranked:
        s = sent.lower()
        if not any(c in s for c in COMMITMENT_CUES):
            continue
        owner, side = _detect_owner(sent, speaker, internal, all_speakers)
        due_hint = None
        m = re.search(
            r"\b(today|tonight|tomorrow|day after tomorrow|next week|next month|this week|"
            r"end of week|by friday|by \w+day|in \w+ (?:day|week|month)s?|on \d{1,2}[/-]\d{1,2}"
            r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)",
            s,
        )
        if m:
            due_hint = m.group(1)
        due = parse_due_date(due_hint, meeting_date) or (
            meeting_date + timedelta(days=SUMMARY_CONFIG["default_action_due_days"])
        )
        lowered = sent.lower().strip()
        if any(lowered.startswith(m) for m in META_PREFIXES):
            continue
        task = re.sub(r"^(so|okay|ok|alright|yeah|yes|right)[,\s]+", "", sent, flags=re.IGNORECASE).strip()
        key = task.lower()[:60]
        if key in seen_tasks or len(task) < 12:
            continue
        # near-duplicate guard: two phrasings of the same commitment collapse to one
        tokens = {w for w in re.findall(r"[a-z]{4,}", task.lower())}
        if any(
            len(tokens & prev) / max(len(tokens | prev), 1) > 0.55
            for prev in action_tokens
        ):
            continue
        seen_tasks.add(key)
        action_tokens.append(tokens)
        actions.append(
            ActionItem(
                task=task[:400],
                owner=owner,
                owner_side=side,  # type: ignore[arg-type]
                due_date=due,
                due_hint=due_hint,
                priority=_priority_for(sent, bool(due_hint)),  # type: ignore[arg-type]
                source_quote=sent[:300],
            )
        )
        if len(actions) >= SUMMARY_CONFIG["max_action_items"]:
            break

    # Present action items in execution order, not extraction order.
    prio_rank = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda a: (prio_rank[a.priority], a.due_date or date.max))

    # 4) key discussion points — one per topic, highest-ranked sentence wins
    points: list[DiscussionPoint] = []
    used_topics: set[str] = set()
    for speaker, sent in ranked:
        topic = _topic_of(sent)
        if topic in used_topics:
            continue
        if _score_sentence(sent) < 1.2:
            continue
        used_topics.add(topic)
        points.append(
            DiscussionPoint(
                topic=topic,
                detail=f"{speaker}: {sent[:280]}",
                sentiment=_sentiment(sent),  # type: ignore[arg-type]
                quote=sent[:300],
            )
        )
        if len(points) >= SUMMARY_CONFIG["max_bullets"]:
            break

    # Fallback: very short or off-topic calls still deserve points.
    if len(points) < 2:
        for speaker, sent in ranked:
            if any(p.quote == sent for p in points):
                continue
            if _score_sentence(sent) < 0.8:
                continue
            points.append(
                DiscussionPoint(
                    topic=_topic_of(sent),
                    detail=f"{speaker}: {sent[:280]}",
                    sentiment=_sentiment(sent),  # type: ignore[arg-type]
                    quote=sent[:300],
                )
            )
            if len(points) >= 2:
                break

    # 5) decisions / objections / competitors / next step
    decisions = list(dict.fromkeys(s for _, s in flat if any(c in s.lower() for c in DECISION_CUES)))[:5]
    objections = list(dict.fromkeys(
        sent for _, sent in flat
        if any(c in sent.lower() for c in OBJECTION_CUES) and _sentiment(sent) == "negative"
    ))[:5]
    competitors = sorted({c.title() for _, s in flat for c in COMPETITOR_NAMES if c in s.lower()})

    next_step = ""
    for _, sent in ranked:
        if any(sent.lower().startswith(m) for m in META_PREFIXES):
            continue
        if any(c in sent.lower() for c in NEXT_STEP_CUES):
            next_step = sent[:300]
            break
    if not next_step and actions:
        next_step = f"Owner-assigned follow-up: {actions[0].task[:200]}"
    elif not next_step:
        next_step = "No explicit next step agreed — recommend a follow-up to confirm commitments."

    # 6) executive summary: a real digest, not concatenated transcript.
    #    Structure mirrors how a rep would write it in the CRM notes field:
    #    who talked -> what was covered -> what was promised -> what is at risk.
    topics_discussed = [p.topic for p in points if p.topic != "general"][:4]
    parts = [
        f"{len(utterances)}-message conversation between "
        f"{', '.join(sorted(all_speakers)) or 'unknown participants'}."
    ]
    if topics_discussed:
        parts.append("Discussed " + ", ".join(topics_discussed) + ".")
    if actions:
        owners = sorted({a.owner for a in actions if a.owner != "unassigned"})
        parts.append(
            f"{len(actions)} commitment{'s' if len(actions) != 1 else ''} captured"
            + (f" ({', '.join(owners)})" if owners else "")
            + "."
        )
    if decisions:
        parts.append(f"Decision recorded: {decisions[0][:160]}")
    if objections:
        parts.append(f"Open objection: {objections[0][:160]}")

    # Add the single highest-value quote for colour, if it is not already covered.
    best_sentence = ranked[0][1] if ranked else ""
    if best_sentence and _score_sentence(best_sentence) >= 2.0:
        parts.append(f"Key quote — “{best_sentence[:220]}”")
    if not next_step and not actions and not topics_discussed:
        parts.append("No commitments or decisions were agreed in this conversation.")

    summary = " ".join(parts)[:1200]

    # 7) talk ratio + sentiment
    internal_words = sum(len(u.text.split()) for u in utterances if u.speaker.lower() in internal)
    total_words = sum(len(u.text.split()) for u in utterances) or 1
    pos = sum(1 for _, s in flat if _sentiment(s) == "positive")
    neg = sum(1 for _, s in flat if _sentiment(s) == "negative")
    overall = "positive" if pos > neg * 1.5 else "negative" if neg > pos * 1.5 else "neutral"

    # Confidence: how much of the transcript actually fed the output.
    signal = (len(actions) * 2 + len(points) + len(decisions)) / max(len(flat), 1)
    confidence = round(min(0.85, 0.30 + signal * 3), 3)  # heuristic caps at 0.85

    return ConversationSummary(
        interaction_id=interaction_id,
        lead_id=lead_id,
        summary=summary,
        key_discussion_points=points,
        action_items=actions,
        decisions=[d[:300] for d in decisions],
        objections=[o[:300] for o in objections],
        competitors_mentioned=competitors,
        next_step=next_step,
        overall_sentiment=overall,  # type: ignore[arg-type]
        talk_ratio_internal=round(internal_words / total_words, 3),
        confidence=confidence,
        engine="heuristic",
        model="rules-v1",
    )


# ---------------------------------------------------------------------------
# LLM engine + validation
# ---------------------------------------------------------------------------
def _coerce_action_items(raw: Any, meeting_date: date) -> list[ActionItem]:
    out: list[ActionItem] = []
    if not isinstance(raw, list):
        return out
    for item in raw[: SUMMARY_CONFIG["max_action_items"]]:
        if not isinstance(item, dict):
            continue
        task = str(item.get("task", "")).strip()
        if len(task) < 4:
            continue
        hint = item.get("due_hint") or item.get("due_date")
        due = parse_due_date(str(hint), meeting_date) if hint else None
        side = str(item.get("owner_side", "unassigned")).lower()
        if side not in {"internal", "customer", "unassigned"}:
            side = "unassigned"
        prio = str(item.get("priority", "medium")).lower()
        try:
            out.append(
                ActionItem(
                    task=task[:400],
                    owner=str(item.get("owner") or "unassigned")[:80],
                    owner_side=side,  # type: ignore[arg-type]
                    due_date=due,
                    due_hint=str(hint)[:80] if hint else None,
                    priority=prio if prio in {"high", "medium", "low"} else "medium",  # type: ignore[arg-type]
                    source_quote=str(item.get("source_quote", ""))[:300],
                )
            )
        except Exception as exc:  # noqa: BLE001 - one bad row must not break the call
            log.warning("dropping malformed action item %s: %s", item, exc)
    return out


def _coerce_points(raw: Any) -> list[DiscussionPoint]:
    out: list[DiscussionPoint] = []
    if not isinstance(raw, list):
        return out
    for item in raw[: SUMMARY_CONFIG["max_bullets"]]:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic", "")).strip() or "general"
        detail = str(item.get("detail", "")).strip()
        if not detail:
            continue
        sent = str(item.get("sentiment", "neutral")).lower()
        out.append(
            DiscussionPoint(
                topic=topic[:80],
                detail=detail[:400],
                sentiment=sent if sent in {"positive", "neutral", "negative"} else "neutral",  # type: ignore[arg-type]
                quote=str(item.get("quote", ""))[:300],
            )
        )
    return out


def llm_summarise(
    utterances: list[Utterance],
    interaction_id: str,
    lead_id: str | None = None,
    meeting_date: date | None = None,
    internal_speakers: set[str] | None = None,
    llm: LLMClient | None = None,
    variant: str = DEFAULT_SUMMARY.version,
) -> ConversationSummary:
    llm = llm or get_llm()
    meeting_date = meeting_date or date.today()
    internal = _internal_speakers(utterances, internal_speakers)

    transcript = "\n".join(
        f"[{u.speaker}{' (internal)' if u.speaker.lower() in internal else ''}] {_clean(u.text)}"
        for u in utterances
    )
    template = get_prompt("meeting_summary", variant)
    system, user = template.render(
        interaction_id=interaction_id,
        meeting_date=meeting_date.isoformat(),
        internal_speakers=", ".join(sorted(internal)) or "not declared",
        transcript=transcript[:24000],
        max_bullets=SUMMARY_CONFIG["max_bullets"],
        max_action_items=SUMMARY_CONFIG["max_action_items"],
    )

    data, resp = llm.chat_json(
        system, user,
        temperature=SUMMARY_CONFIG["temperature"],
        max_tokens=1600,
    )

    fallback = heuristic_summarise(
        utterances, interaction_id, lead_id, meeting_date, internal_speakers
    )
    actions = _coerce_action_items(data.get("action_items"), meeting_date)
    points = _coerce_points(data.get("key_discussion_points"))

    # Guard: an LLM that returns nothing usable must not blank the CRM record.
    if not actions and not points and not str(data.get("summary", "")).strip():
        log.warning("LLM summary empty for %s — falling back to heuristic", interaction_id)
        return fallback

    summary_text = str(data.get("summary", "")).strip() or fallback.summary
    overall = str(data.get("overall_sentiment", fallback.overall_sentiment)).lower()
    if overall not in {"positive", "neutral", "negative"}:
        overall = fallback.overall_sentiment

    completeness = (
        (1.0 if summary_text else 0)
        + (1.0 if points else 0)
        + (1.0 if actions else 0)
        + (1.0 if data.get("next_step") else 0)
    ) / 4.0
    confidence = round(min(0.97, 0.55 + 0.4 * completeness), 3)

    return ConversationSummary(
        interaction_id=interaction_id,
        lead_id=lead_id,
        summary=summary_text[:1200],
        key_discussion_points=points or fallback.key_discussion_points,
        action_items=actions,
        decisions=[str(d)[:300] for d in (data.get("decisions") or [])][:5],
        objections=[str(o)[:300] for o in (data.get("objections") or [])][:5],
        competitors_mentioned=[str(c)[:60] for c in (data.get("competitors_mentioned") or [])][:8],
        next_step=str(data.get("next_step", "")).strip()[:300] or fallback.next_step,
        overall_sentiment=overall,  # type: ignore[arg-type]
        talk_ratio_internal=fallback.talk_ratio_internal,
        confidence=confidence,
        engine="llm",
        model=resp.model,
    )


def summarise(
    utterances: list[Utterance],
    interaction_id: str,
    lead_id: str | None = None,
    meeting_date: date | None = None,
    internal_speakers: set[str] | None = None,
    llm: LLMClient | None = None,
    prefer_llm: bool = True,
    variant: str = DEFAULT_SUMMARY.version,
) -> ConversationSummary:
    """Public entry point: LLM when available, heuristic otherwise. Never raises
    for provider problems — the endpoint must stay up."""
    if not utterances:
        raise ValueError("utterances cannot be empty")
    if prefer_llm:
        try:
            return llm_summarise(
                utterances, interaction_id, lead_id, meeting_date,
                internal_speakers, llm=llm or get_llm(), variant=variant,
            )
        except (LLMUnavailable, KeyError, ValueError) as exc:
            log.info("LLM summarisation unavailable (%s) — using heuristic engine", exc)
    return heuristic_summarise(utterances, interaction_id, lead_id, meeting_date, internal_speakers)


# ---------------------------------------------------------------------------
# CRM write-back helper (Sales_Interactions / action items)
# ---------------------------------------------------------------------------
def to_interaction_record(summary: ConversationSummary) -> dict[str, Any]:
    """Shape a summary for the Sales_Interactions table + activity feed."""
    return {
        "interaction_id": summary.interaction_id,
        "lead_id": summary.lead_id,
        "interaction_type": "meeting",
        "summary": summary.summary,
        "key_points": [p.model_dump() for p in summary.key_discussion_points],
        "action_items": [a.model_dump(mode="json") for a in summary.action_items],
        "decisions": summary.decisions,
        "objections": summary.objections,
        "competitors_mentioned": summary.competitors_mentioned,
        "next_step": summary.next_step,
        "sentiment": summary.overall_sentiment,
        "talk_ratio_internal": summary.talk_ratio_internal,
        "confidence": summary.confidence,
        "engine": summary.engine,
        "model": summary.model,
        "created_at": summary.created_at.isoformat(),
        "open_action_count": sum(1 for a in summary.action_items),
        "high_priority_count": sum(1 for a in summary.action_items if a.priority == "high"),
    }
