"""Day 15 — Next-Best-Action (NBA) recommendation engine (Module 4).

Given a scored lead plus its interaction history, decide *what to do next*:

1. **Priority** (P0..P3) — blends lead score, deal value, deal stage and staleness.
2. **Follow-up timing** — a concrete next-touch date, derived from stage, score,
   responsiveness and the contact-frequency guardrails.
3. **Channel mix** — which channels to use, in what order and proportion.
4. **Content strategy** — content type, angle, key messages, CTA, tone.

Design constraints that came out of the Milestone-2 review:
  * deterministic and explainable — every output carries `rationale` strings;
  * never recommends contact that violates guardrails (DNC, quiet hours,
    frequency caps) — it returns `suppress=True` instead;
  * the LLM only ever *writes copy*; it never decides timing or priority.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sales_intel.ai.scoring.engine import load_scoring_config, score_lead
from sales_intel.config import NBA_CONFIG
from sales_intel.schemas import (
    ChannelAllocation,
    ContentStrategy,
    LeadContext,
    LeadFeatures,
    LeadScore,
    NextBestAction,
    Touch,
)

log = logging.getLogger(__name__)

# Stage -> (base follow-up delay in days, urgency multiplier)
STAGE_DELAY: dict[str, tuple[int, float]] = {
    "negotiation": (1, 1.35),
    "proposal": (2, 1.25),
    "qualified": (3, 1.10),
    "contacted": (4, 1.00),
    "new": (2, 1.05),
    "nurture": (21, 0.60),
    "won": (30, 0.50),
    "lost": (45, 0.40),
}

CHANNEL_BY_STAGE: dict[str, list[str]] = {
    "new": ["email", "linkedin", "call"],
    "contacted": ["email", "call", "linkedin"],
    "qualified": ["email", "call", "meeting"],
    "proposal": ["email", "call", "meeting"],
    "negotiation": ["call", "email", "meeting"],
    "nurture": ["email", "linkedin"],
    "won": ["email"],
    "lost": ["email"],
}

CONTENT_BY_STAGE: dict[str, tuple[str, str]] = {
    "new": ("cold_outreach", "insight_led_hook"),
    "contacted": ("follow_up", "value_reminder"),
    "qualified": ("case_study", "peer_proof"),
    "proposal": ("proposal_walkthrough", "commercial_clarity"),
    "negotiation": ("objection_handling", "risk_reversal"),
    "nurture": ("newsletter", "thought_leadership"),
    "won": ("onboarding", "expansion"),
    "lost": ("win_back", "what_changed"),
}

CTA_BY_STAGE: dict[str, str] = {
    "new": "Would it be worth a 15-minute call next week to sanity-check this?",
    "contacted": "Open to a quick 15-minute walkthrough on Thursday or Friday?",
    "qualified": "Shall I send a tailored 30-minute demo invite for next week?",
    "proposal": "Can we book 20 minutes to walk through the proposal together?",
    "negotiation": "Can we lock the final terms on a 15-minute call tomorrow?",
    "nurture": "Want me to keep sending these monthly, or is now not the time?",
    "won": "Shall I set up the onboarding kickoff for the week of the go-live?",
    "lost": "Worth revisiting in the new quarter if priorities shift?",
}

ANGLE_BY_SENIORITY: dict[str, str] = {
    "c_level": "business outcome, risk and time-to-value",
    "vp": "pipeline impact, team efficiency and forecast accuracy",
    "director": "operational throughput and adoption inside the team",
    "manager": "day-to-day workflow relief and quick wins",
    "unknown": "practical value and ease of getting started",
}

ASSET_BY_INDUSTRY: dict[str, str] = {
    "saas": "a 1-page ROI model built on their pricing tier",
    "manufacturing": "a distributor-network case study",
    "bfsi": "a compliance-safe reference architecture brief",
    "healthcare": "a data-privacy one-pager plus a peer hospital case",
    "retail": "a footfall-to-conversion benchmark deck",
    "logistics": "a route-to-cash cycle-time teardown",
}
DEFAULT_ASSET = "a 2-page one-pager with two relevant customer stories"

TONE_BY_STAGE: dict[str, str] = {
    "new": "direct and curiosity-driven",
    "contacted": "warm and specific",
    "qualified": "consultative",
    "proposal": "clear and commercially precise",
    "negotiation": "steady and assurance-led",
    "nurture": "helpful and low-pressure",
    "won": "partnership-oriented",
    "lost": "gracious and open",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _days_since(ts: datetime | None, today: date) -> int | None:
    if ts is None:
        return None
    return (today - ts.date()).days


def _is_business_day(d: date) -> bool:
    return d.weekday() not in NBA_CONFIG["no_contact_weekdays"]


def _next_business_day(d: date) -> date:
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


def _last_outcome(ctx: LeadContext) -> str | None:
    if not ctx.history:
        return None
    latest = max(ctx.history, key=lambda h: h.occurred_at)
    return latest.outcome


def _channel_scores(ctx: LeadContext, score: LeadScore) -> dict[str, float]:
    """Score each channel 0..1 from history, stage and persona."""
    allowed = set(CHANNEL_BY_STAGE.get(ctx.lifecycle_stage, ["email"]))
    perf: dict[str, list[float]] = {}
    for h in ctx.history:
        if h.channel == "none":
            continue
        val = {"no_response": 0.0, "opened": 0.3, "replied": 0.7, "positive": 0.9,
               "negative": 0.1, "meeting_booked": 1.0}[h.outcome]
        perf.setdefault(h.channel, []).append(val)

    persona_pref = NBA_CONFIG["channel_preference_by_seniority"].get(
        ctx.seniority, ["email", "call", "linkedin"]
    )
    out: dict[str, float] = {}
    for ch in ["email", "call", "linkedin", "whatsapp", "meeting"]:
        if ch not in allowed and ch != "meeting":
            continue
        hist = sum(perf[ch]) / len(perf[ch]) if ch in perf else 0.25  # neutral prior
        pref = 1.0 if ch in persona_pref[:1] else 0.7 if ch in persona_pref else 0.4
        stage_fit = 1.0 if ch in CHANNEL_BY_STAGE.get(ctx.lifecycle_stage, []) else 0.5
        # A meeting ask only makes sense once the lead is genuinely warm.
        if ch == "meeting" and score.score < NBA_CONFIG["meeting_ask_after_score"]:
            continue
        out[ch] = round(0.55 * hist + 0.25 * pref + 0.20 * stage_fit, 4)
    if not out:
        out["email"] = 0.5
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def _priority(score: LeadScore, ctx: LeadContext, days_since: int | None) -> tuple[str, float, list[str]]:
    """Blend lead score, deal value and stage maturity into a 0-100 priority.

    A purely additive formula saturates at 100 for strong leads, which destroys
    the ordering *within* the top of the queue (a negotiation lead stops
    outranking a freshly-qualified one). We therefore use a bounded weighted
    blend, plus a multiplicative staleness decay.
    """
    import math

    rationale: list[str] = []

    # 1) Deal value, log-scaled: $1k -> 0, $100k -> 100.
    if ctx.deal_value_usd > 0:
        value_component = 100.0 * min(1.0, math.log10(max(ctx.deal_value_usd, 1000) / 1000) / 2.0)
    else:
        value_component = 0.0
    rationale.append(f"lead score {score.score:.1f} ({score.band}) · 70% of priority")

    # 2) Stage maturity.
    stage_component = {
        "negotiation": 100.0, "proposal": 90.0, "qualified": 80.0, "contacted": 70.0,
        "new": 60.0, "nurture": 20.0, "won": 10.0, "lost": 0.0,
    }[ctx.lifecycle_stage]
    rationale.append(
        f"stage '{ctx.lifecycle_stage}' maturity {stage_component:.0f}/100 · 15% of priority"
    )
    rationale.append(
        f"deal value ${ctx.deal_value_usd:,.0f} → {value_component:.0f}/100 · 15% of priority"
    )

    blended = 0.70 * score.score + 0.15 * value_component + 0.15 * stage_component

    if ctx.decision_maker:
        blended += 3.0
        rationale.append("verified decision-maker adds 3.0")

    # 3) Multiplicative staleness decay: up to -30% for very old contacts.
    if days_since is not None and days_since > NBA_CONFIG["stale_after_days"]:
        decay = min(0.30, 0.02 * (days_since - NBA_CONFIG["stale_after_days"]))
        blended *= (1.0 - decay)
        rationale.append(
            f"{days_since} days since last contact decays priority by {decay:.0%}"
        )

    total = round(max(0.0, min(100.0, blended)), 2)
    priority = "P0" if total >= 80 else "P1" if total >= 60 else "P2" if total >= 40 else "P3"
    return priority, total, rationale


def _next_touch_date(
    ctx: LeadContext, score: LeadScore, days_since: int | None, today: date
) -> tuple[date, list[str]]:
    base_delay, mult = STAGE_DELAY.get(ctx.lifecycle_stage, (4, 1.0))
    reasons = [f"stage '{ctx.lifecycle_stage}' base delay {base_delay}d"]

    # Highly engaged leads get contacted sooner; cold ones later.
    factor = 1.35 - (score.score / 100.0) * 0.9  # 1.35 (score 0) .. 0.45 (score 100)
    reasons.append(f"engagement factor {factor:.2f} from score {score.score:.1f}")

    # Don't chase someone you spoke to an hour ago.
    if days_since is not None and days_since < base_delay:
        remain = max(1, base_delay - days_since)
        delay = remain
        reasons.append(f"only {days_since}d since last touch — hold {remain}d")
    else:
        delay = max(1, round(base_delay * factor / mult))

    # If they replied positively, move fast.
    if _last_outcome(ctx) in {"replied", "positive", "meeting_booked"}:
        delay = max(1, delay - 1)
        reasons.append("last touch was positive — compressed by 1 day")

    target = _next_business_day(today + timedelta(days=delay))
    return target, reasons


def _channel_mix(channel_scores: dict[str, float]) -> list[ChannelAllocation]:
    top = list(channel_scores.items())[:3]
    total = sum(v for _, v in top) or 1.0
    shares = [max(10, round(v / total * 100)) for _, v in top]
    diff = 100 - sum(shares)
    shares[0] += diff  # absorb rounding on the primary channel
    out = []
    for (ch, sc), share in zip(top, shares):
        why = (
            "historically the strongest response channel for this contact"
            if sc >= 0.6
            else "preferred channel for this persona and stage"
            if sc >= 0.45
            else "supporting channel — keeps the multi-touch sequence alive"
        )
        out.append(ChannelAllocation(channel=ch, share=share, rationale=why))
    return out


def _cadence(
    ctx: LeadContext, next_date: date, primary: str, mix: list[ChannelAllocation]
) -> list[Touch]:
    offsets = NBA_CONFIG["cadence_offsets_days"][: 2 if ctx.lifecycle_stage in {"nurture", "won", "lost"} else 4]
    purposes = {
        "email": "value-led follow-up with one clear ask",
        "call": "live discovery / objection handling",
        "linkedin": "light-touch engagement (comment or connect note)",
        "whatsapp": "short nudge where culturally appropriate",
        "meeting": "booked working session",
    }
    channels = [a.channel for a in mix] or [primary]
    cadence: list[Touch] = []
    for i, off in enumerate(offsets):
        ch = channels[i % len(channels)]
        cadence.append(
            Touch(
                step=i + 1,
                offset_days=off,
                channel=ch,  # type: ignore[arg-type]
                purpose=purposes[ch],
                planned_at=_next_business_day(next_date + timedelta(days=off)),
            )
        )
    return cadence


def _content(
    ctx: LeadContext, score: LeadScore, llm_copy: dict[str, Any] | None = None
) -> ContentStrategy:
    content_type, angle = CONTENT_BY_STAGE.get(ctx.lifecycle_stage, ("follow_up", "value_reminder"))
    asset = ASSET_BY_INDUSTRY.get(ctx.industry.lower().strip(), DEFAULT_ASSET)
    if ctx.industry_tags:
        asset = f"{asset} (highlighting {ctx.industry_tags[0]})"

    messages: list[str] = []
    for p in ctx.pain_points[:2]:
        messages.append(f"Acknowledge the '{p}' pain explicitly and tie it to a concrete outcome.")
    messages.append(
        f"Lead with {ANGLE_BY_SENIORITY.get(ctx.seniority, ANGLE_BY_SENIORITY['unknown'])}."
    )
    if score.subscores.get("intent", 0) >= 60:
        messages.append("Intent signals are high — reference their recent research instead of re-educating.")
    if ctx.lifecycle_stage in {"proposal", "negotiation"}:
        messages.append("Assume technical fit is settled; spend the words on risk, timeline and commercials.")
    if _last_outcome(ctx) == "no_response":
        messages.append("Previous touch got no reply — change the angle, not just the wording.")

    hooks = [
        f"{ctx.company_name or 'the account'} · {ctx.industry or 'industry'} context",
    ]
    if ctx.pain_points:
        hooks.append(f"pain point: {ctx.pain_points[0]}")
    if ctx.decision_maker:
        hooks.append("speaks as decision-maker — skip the gatekeeper framing")

    if llm_copy:
        return ContentStrategy(
            content_type=llm_copy.get("content_type", content_type),
            angle=llm_copy.get("angle", angle),
            key_messages=llm_copy.get("key_messages", messages),
            suggested_asset=llm_copy.get("suggested_asset", asset),
            call_to_action=llm_copy.get("call_to_action", CTA_BY_STAGE[ctx.lifecycle_stage]),
            tone=llm_copy.get("tone", TONE_BY_STAGE[ctx.lifecycle_stage]),
            personalisation_hooks=hooks,
        )

    return ContentStrategy(
        content_type=content_type,
        angle=angle,
        key_messages=messages[:5],
        suggested_asset=asset,
        call_to_action=CTA_BY_STAGE.get(ctx.lifecycle_stage, "Open to a quick call?"),
        tone=TONE_BY_STAGE.get(ctx.lifecycle_stage, "consultative"),
        personalisation_hooks=hooks,
    )


def _guardrails(
    ctx: LeadContext, priority: str, mix: list[ChannelAllocation], today: date
) -> tuple[bool, str | None, list[str]]:
    risks: list[str] = []
    if ctx.do_not_contact:
        return True, "lead is flagged do-not-contact", ["DNC flag set — suppressed"]
    touches_14d = [h for h in ctx.history if (today - h.occurred_at.date()).days <= 14]
    cap = NBA_CONFIG["max_touches_per_14_days"][priority]
    if len(touches_14d) >= cap:
        return (
            True,
            f"frequency cap reached ({len(touches_14d)}/{cap} touches in 14 days)",
            [f"contact-frequency guardrail hit: {len(touches_14d)}/{cap} in last 14 days"],
        )
    if ctx.local_hour is not None:
        qh = NBA_CONFIG["quiet_hours"]
        if ctx.local_hour >= qh["start"] or ctx.local_hour < qh["end"]:
            risks.append(
                f"local hour {ctx.local_hour}:00 is inside quiet hours "
                f"({qh['start']}:00-{qh['end']}:00) — schedule send for next business morning"
            )
    negatives = [h for h in ctx.history[-3:] if h.outcome == "negative"]
    if len(negatives) >= 2:
        risks.append("two of the last three touches were negative — consider switching to nurture")
    if ctx.lifecycle_stage == "won":
        risks.append("closed-won account: route to onboarding/expansion, not pipeline motions")
    if len(mix) == 1:
        risks.append("only one viable channel — sequence depends on a single touchpoint")
    return False, None, risks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def recommend(
    lead: LeadFeatures,
    ctx: LeadContext,
    today: date | None = None,
    scoring_config: dict[str, Any] | None = None,
    score: LeadScore | None = None,
) -> NextBestAction:
    """Produce the next-best-action for one lead."""
    today = today or date.today()
    score = score or score_lead(lead, scoring_config or load_scoring_config())
    days_since = _days_since(ctx.last_contact_at, today)

    priority, priority_score, priority_reasons = _priority(score, ctx, days_since)
    next_date, timing_reasons = _next_touch_date(ctx, score, days_since, today)

    channel_scores = _channel_scores(ctx, score)
    mix = _channel_mix(channel_scores)
    primary = mix[0].channel
    cadence = _cadence(ctx, next_date, primary, mix)
    content = _content(ctx, score)

    suppress, suppress_reason, risks = _guardrails(ctx, priority, mix, today)
    if days_since is not None and days_since > NBA_CONFIG["stale_after_days"]:
        risks.append(f"lead marked stale ({days_since}d since last touch)")

    rationale = [
        *priority_reasons,
        *timing_reasons,
        f"primary channel '{primary}' chosen from: "
        + ", ".join(f"{k}({v:.2f})" for k, v in channel_scores.items()),
        f"content type '{content.content_type}' matches stage '{ctx.lifecycle_stage}'",
        f"persona '{ctx.seniority}' framed around {ANGLE_BY_SENIORITY.get(ctx.seniority, 'practical value')}",
    ]

    return NextBestAction(
        lead_id=ctx.lead_id,
        priority=priority,  # type: ignore[arg-type]
        priority_score=priority_score,
        recommended_channel=primary,  # type: ignore[arg-type]
        next_touch_date=next_date,
        days_since_last_contact=days_since,
        cadence=cadence,
        channel_mix=mix,
        content=content,
        rationale=rationale,
        risk_flags=risks,
        suppress=suppress,
        suppress_reason=suppress_reason,
    )


def recommend_batch(
    pairs: list[tuple[LeadFeatures, LeadContext]],
    today: date | None = None,
    scoring_config: dict[str, Any] | None = None,
) -> list[NextBestAction]:
    """Score once, recommend for all, return sorted by priority (queue order)."""
    cfg = scoring_config or load_scoring_config()
    out = [recommend(lead, ctx, today=today, scoring_config=cfg) for lead, ctx in pairs]
    return sorted(out, key=lambda a: (-a.priority_score, a.next_touch_date))
