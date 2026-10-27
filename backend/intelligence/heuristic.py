"""Deterministic, offline intelligence engine.

This engine exists so the backend can be developed, tested and demonstrated
without an external model provider or API key.  It is deliberately transparent:

* it never claims to have researched a company externally;
* it separates supplied facts from hypotheses;
* its score is an explainable heuristic over the four factors required by
  SRS FR-030 (engagement, fit, intent, decision readiness) and is *not* a
  trained or calibrated conversion model;
* it never invents dates, owners or commitments from a transcript.

It is not a substitute for the reviewed AI package; see
``backend/intelligence/external.py`` for the integration adapter.
"""
from __future__ import annotations

import re
import time
from typing import Any

from backend.config import Settings
from backend.intelligence.contract import (
    ActionItem,
    ConversationSummary,
    EvidenceItem,
    ExecutionInfo,
    Hypothesis,
    LeadIntelligence,
    LeadScoreResult,
    OutreachDraft,
    QualificationAssessment,
    Recommendation,
    SalesInsight,
    SalesInsightsResult,
    ScoreFactor,
)

MODEL_VERSION = "deterministic-heuristic-v1"

_FACT_FIELDS: tuple[tuple[str, str], ...] = (
    ("industry", "Industry"),
    ("company_size", "Company size"),
    ("company_description", "Company description"),
    ("prospect_role", "Prospect role"),
    ("explicit_needs", "Stated need"),
    ("user_research", "User-provided research"),
)

_SENIOR_ROLE_WORDS = (
    "chief", "cto", "ceo", "cfo", "coo", "vp", "vice president", "head",
    "director", "owner", "founder", "partner", "manager", "president",
)

_ENGAGEMENT_WORDS = ("meeting", "demo", "call", "replied", "responded", "opened", "booked")

_NEGATIVE_WORDS = ("no response", "unsubscribed", "declined", "not interested", "bounced")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _contains(value: str, words: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(word in lowered for word in words)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [part.strip() for part in parts if len(part.strip()) > 10]


class HeuristicEngine:
    """Offline implementation of :class:`~backend.intelligence.contract.IntelligenceEngine`."""

    name = "heuristic"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = "heuristic"
        self.model = MODEL_VERSION

    # -- helpers ---------------------------------------------------------
    def _execution(self, started: float) -> ExecutionInfo:
        return ExecutionInfo(
            engine=self.name,
            provider=self.provider,
            model=self.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            used_mock=True,
        )

    # -- Module 2: company analysis / lead intelligence -------------------
    def analyze_lead(self, lead: dict[str, Any]) -> tuple[LeadIntelligence, ExecutionInfo]:
        started = time.perf_counter()
        company = _text(lead.get("company_name")) or "This company"
        industry = _text(lead.get("industry"))
        product = _text(lead.get("product_service")) or "the offering"

        facts: list[EvidenceItem] = []
        for field, label in _FACT_FIELDS:
            value = _text(lead.get(field))
            if value:
                facts.append(
                    EvidenceItem(
                        statement=f"{label}: {value}",
                        source="Supplied lead record",
                        source_type="backend",
                        confidence="high" if field in {"industry", "prospect_role"} else "medium",
                    )
                )

        missing: list[str] = []
        for field, label in (
            ("website", "Website or retrieved company material"),
            ("company_description", "Company description"),
            ("prospect_role", "Prospect role and buying influence"),
            ("explicit_needs", "Confirmed customer need"),
            ("engagement_history", "Engagement history"),
        ):
            if not _text(lead.get(field)):
                missing.append(label)

        needs: list[Hypothesis]
        explicit = _text(lead.get("explicit_needs"))
        if explicit:
            needs = [
                Hypothesis(
                    statement=explicit,
                    rationale="Stated explicitly in the supplied lead record.",
                    confidence="medium",
                    requires_validation=False,
                )
            ]
        else:
            needs = [
                Hypothesis(
                    statement=f"Validate whether {product} addresses a current priority for {company}.",
                    rationale="No explicit need was supplied; this is a discovery hypothesis only.",
                )
            ]

        challenges = [
            Hypothesis(
                statement=f"{company} may have an unmet workflow need related to {product}.",
                rationale="Derived from the supplied context; not independently verified.",
            )
        ]
        if _contains(industry + " " + _text(lead.get("company_description")), ("growth", "scale", "expanding")):
            challenges.append(
                Hypothesis(
                    statement="Growth may be creating process or capacity pressure.",
                    rationale="The supplied description references growth or scale.",
                    confidence="medium",
                )
            )

        role = _text(lead.get("prospect_role"))
        qualification = self._qualify(lead, facts, missing)

        result = LeadIntelligence(
            company_overview=(
                f"{company} is described only through the supplied lead record. "
                "No website retrieval or external research was performed."
            ),
            supported_facts=facts,
            potential_challenges=challenges,
            possible_needs=needs,
            opportunities=[
                Hypothesis(
                    statement=f"Explore whether {product} can support {company}'s stated priorities.",
                    rationale="Potential opportunity; requires discovery confirmation.",
                )
            ],
            product_industry_fit=(
                f"Fit cannot be confirmed from the available context. Compare {product} with the "
                f"{industry or 'unknown'} industry and validate during discovery."
            ),
            buyer_role_relevance=(
                f"Recorded role is {role}; confirm decision authority and stakeholders."
                if role
                else "No buyer role supplied; identify the economic buyer, users and champion."
            ),
            qualification_insights=[
                "Treat all opportunity statements as hypotheses until the customer validates them."
            ],
            discovery_questions=[
                f"What priority would make evaluating {product} worthwhile?",
                "How is this handled today and what is not working?",
                "Who else would evaluate or approve a change?",
                "What outcome and timing would define success?",
            ],
            missing_information=missing,
            qualification=qualification,
            confidence="medium" if len(facts) >= 3 else "low",
        )
        return result, self._execution(started)

    def _qualify(
        self, lead: dict[str, Any], facts: list[EvidenceItem], missing: list[str]
    ) -> QualificationAssessment:
        role = _text(lead.get("prospect_role"))
        needs = _text(lead.get("explicit_needs"))
        engagement = _text(lead.get("engagement_history"))
        senior = _contains(role, _SENIOR_ROLE_WORDS)
        signals: list[str] = []
        if needs:
            signals.append("An explicit customer need was supplied.")
        if senior:
            signals.append(f"The recorded role ({role}) suggests decision influence.")
        if _contains(engagement, _ENGAGEMENT_WORDS):
            signals.append("Engagement history contains a meaningful interaction.")

        if needs and (senior or _contains(engagement, _ENGAGEMENT_WORDS)):
            category = "Qualified"
            confidence = "medium"
        elif len(facts) >= 3:
            category = "Nurture"
            confidence = "medium"
        else:
            category = "Needs discovery"
            confidence = "low"

        gaps = list(missing)
        if not engagement:
            gaps.append("No engagement signal is available.")

        return QualificationAssessment(
            category=category,
            fit_assessment=(
                "Enough supplied context exists for a discovery hypothesis."
                if len(facts) >= 3
                else "Company fit is not yet established from the supplied context."
            ),
            buyer_relevance=(
                f"{role} should be validated for decision influence and ownership."
                if role
                else "No buyer role is available."
            ),
            engagement_assessment=engagement or "No engagement history was supplied.",
            positive_signals=signals,
            risks_or_gaps=gaps,
            recommended_next_step=(
                "Run a focused discovery conversation to validate need, stakeholders, "
                "urgency and the current process."
            ),
            confidence=confidence,
        )

    # -- Module 3: outreach ----------------------------------------------
    def generate_outreach(
        self, lead: dict[str, Any], request: dict[str, Any]
    ) -> tuple[OutreachDraft, ExecutionInfo]:
        started = time.perf_counter()
        company = _text(lead.get("company_name")) or "your team"
        contact = _text(lead.get("contact_name"))
        first_name = contact.split()[0] if contact else "there"
        industry = _text(request.get("industry")) or _text(lead.get("industry"))
        goal = _text(request.get("goal")) or "start a discovery conversation"
        product = _text(request.get("product_service")) or "our solution"
        tone = _text(request.get("tone")).lower() or "professional"
        length = _text(request.get("length")).lower() or "medium"
        outreach_type = _text(request.get("outreach_type")).lower() or "cold_email"
        pain_points = [str(p).strip() for p in request.get("pain_points") or [] if str(p).strip()]
        cta = _text(request.get("call_to_action")) or "Would a short conversation next week be useful?"

        channel = {
            "linkedin_message": "LinkedIn",
            "call_script": "Call script",
            "short_message": "Short message",
        }.get(outreach_type, "Email")

        facts: list[EvidenceItem] = []
        if industry:
            facts.append(
                EvidenceItem(
                    statement=f"Industry: {industry}",
                    source="Supplied lead record",
                    source_type="backend",
                    confidence="medium",
                )
            )
        for point in pain_points:
            facts.append(
                EvidenceItem(
                    statement=f"Supplied pain point: {point}",
                    source="User-provided outreach inputs",
                    source_type="provided",
                    confidence="medium",
                )
            )

        assumptions: list[str] = []
        if not pain_points:
            assumptions.append(
                "No pain point was supplied; the message avoids asserting a specific problem."
            )
        if not industry:
            assumptions.append("Industry is unknown; the message avoids industry-specific claims.")

        industry_line = f" I understand {company} operates in {industry}." if industry else ""
        pain_line = (
            " You mentioned challenges around " + ", ".join(pain_points[:3]) + "."
            if pain_points
            else ""
        )
        greeting = f"Hi {first_name},"
        opener = f"I am reaching out because {goal}."

        if channel == "Call script":
            subject = None
            body = (
                f"{greeting} this is [Your name] from [Your company]. {opener}"
                f"{industry_line}{pain_line} We help teams evaluate {product}. "
                f"Before assuming relevance, how are you approaching this today? {cta}"
            )
        elif channel == "LinkedIn":
            subject = None
            body = (
                f"{greeting} {opener}{industry_line}{pain_line} "
                f"We help teams explore {product}. {cta}"
            )
        elif channel == "Short message":
            subject = None
            body = f"{greeting} {opener}{pain_line} {cta}"
        else:
            subject = f"A question about {company}'s priorities"
            body = (
                f"{greeting}\n\n{opener}{industry_line}{pain_line}\n\n"
                f"We help teams explore {product} when it is relevant to their current "
                "priorities. I do not want to assume this is a fit.\n\n"
                f"{cta}\n\nBest regards,\n[Your name]"
            )

        if tone == "direct":
            body = body.replace("I do not want to assume this is a fit.\n\n", "")
        elif tone == "friendly":
            body = body.replace("Best regards,", "Best,")
        elif tone == "formal":
            body = body.replace(greeting, f"Dear {first_name},")

        if length == "short" and channel == "Email":
            body = f"{greeting}\n\n{opener}{pain_line}\n\n{cta}\n\nBest regards,\n[Your name]"
        elif length == "long" and channel == "Email":
            body += (
                "\n\nIf it helps, I can share a short outline of how comparable teams "
                "structured this evaluation before we speak."
            )

        draft = OutreachDraft(
            channel=channel,
            subject_line=subject,
            body=body,
            call_to_action=cta,
            personalization_rationale=[
                f"Addressed to {company} using the supplied lead record.",
                f"Channel and length follow the requested {outreach_type}/{length} settings.",
            ],
            facts_used=facts,
            assumptions=assumptions,
            missing_context=[
                label
                for label, value in (
                    ("Confirmed pain point", bool(pain_points)),
                    ("Buying timing", False),
                    ("Named decision maker", bool(contact)),
                )
                if not value
            ],
            alternative_angle=(
                "Test a shorter, question-led angle after the first reply to compare response rates."
            ),
        )
        return draft, self._execution(started)

    # -- Module 5: conversation intelligence ------------------------------
    def summarize_conversation(
        self, transcript: str, notes: str
    ) -> tuple[ConversationSummary, ExecutionInfo]:
        started = time.perf_counter()
        combined = "\n".join(part for part in (transcript.strip(), notes.strip()) if part)
        sentences = _sentences(combined)

        def matching(words: tuple[str, ...], limit: int = 5) -> list[str]:
            return [s for s in sentences if _contains(s, words)][:limit]

        actions: list[ActionItem] = []
        for sentence in matching(
            ("will send", "will share", "will schedule", "will provide", "action item", "follow up")
        ):
            owner_match = re.match(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|to)\b", sentence)
            date_match = re.search(
                r"\b(?:by|on)\s+([A-Z][a-z]+\s+\d{1,2}(?:,?\s+\d{4})?|\d{4}-\d{2}-\d{2})",
                sentence,
            )
            actions.append(
                ActionItem(
                    action=sentence,
                    owner=owner_match.group(1) if owner_match else None,
                    due_date=date_match.group(1) if date_match else None,
                    evidence=sentence,
                    confidence="high" if owner_match or date_match else "medium",
                )
            )

        uncertain: list[str] = []
        if not actions:
            uncertain.append("No explicit action item, owner or due date was detected.")
        requirements = matching(("need", "require", "must", "want", "looking for"))
        if not requirements:
            uncertain.append("No explicit customer requirement was detected.")

        summary = " ".join(sentences[:3]) if sentences else "No analyzable content was supplied."
        result = ConversationSummary(
            executive_summary=summary,
            key_discussion_points=sentences[:6],
            customer_requirements=requirements,
            pain_points=matching(("pain", "problem", "challenge", "slow", "manual", "difficult")),
            objections=matching(("concern", "objection", "budget", "price", "risk", "not sure")),
            product_interests=matching(("interested", "feature", "integration", "demo", "product")),
            buying_signals=matching(("timeline", "budget", "evaluate", "proposal", "purchase")),
            competitor_mentions=matching(("competitor", "alternative", "versus", "vs.")),
            decisions_and_commitments=matching(("decided", "agreed", "committed", "approved")),
            action_items=actions,
            suggested_follow_up=(
                "Send a concise recap that separates confirmed points from open questions, "
                "then ask for the next agreed step."
            ),
            missing_or_uncertain=uncertain,
        )
        return result, self._execution(started)

    # -- Module 4: scoring ------------------------------------------------
    def score_lead(self, lead: dict[str, Any]) -> tuple[LeadScoreResult, ExecutionInfo]:
        started = time.perf_counter()
        industry = _text(lead.get("industry"))
        description = _text(lead.get("company_description"))
        size = _text(lead.get("company_size"))
        role = _text(lead.get("prospect_role"))
        engagement = _text(lead.get("engagement_history"))
        needs = _text(lead.get("explicit_needs"))
        stage = _text(lead.get("stage")) or _text(lead.get("lifecycle_stage")) or "prospecting"
        response = _text(lead.get("response_behavior"))

        # --- fit (30) ---
        fit_parts = {
            "industry identified": (0.35, bool(industry)),
            "company description available": (0.35, len(description) > 35),
            "company size known": (0.30, bool(size) and size.lower() != "unknown"),
        }
        fit = sum(weight for weight, present in fit_parts.values() if present)

        # --- intent (25) ---
        intent = 0.0
        if len(needs) > 15:
            intent += 0.60
        elif needs:
            intent += 0.30
        if _contains(response, ("positive", "interested", "responded", "replied", "booked")):
            intent += 0.40
        elif _contains(response, _NEGATIVE_WORDS):
            intent += 0.0

        # --- engagement (25) ---
        if _contains(engagement, _ENGAGEMENT_WORDS):
            engagement_value = 1.0
        elif engagement:
            engagement_value = 0.40
        else:
            engagement_value = 0.0

        # --- decision readiness (20) ---
        readiness = 0.0
        if _contains(role, _SENIOR_ROLE_WORDS):
            readiness += 0.60
        elif role:
            readiness += 0.30
        if stage in {"proposal", "negotiation"}:
            readiness += 0.40
        elif stage in {"qualified", "discovery"}:
            readiness += 0.25
        else:
            readiness += 0.05

        def factor(
            name: str, weight: float, value: float, explanation: str, dimension: str
        ) -> ScoreFactor:
            value = max(0.0, min(1.0, value))
            if value == 0:
                signal = "missing"
            elif value >= 0.6:
                signal = "positive"
            elif value < 0.3:
                signal = "negative"
            else:
                signal = "neutral"
            return ScoreFactor(
                name=name,
                weight=weight,
                normalized_value=round(value, 4),
                points=round(weight * value, 2),
                explanation=explanation,
                signal=signal,
                dimension=dimension,
            )

        factors = [
            factor(
                "Company fit",
                30,
                fit,
                "Signals present: "
                + (", ".join(k for k, (_, present) in fit_parts.items() if present) or "none"),
                "Fit",
            ),
            factor(
                "Intent",
                25,
                intent,
                "Explicit need and response behaviour indicators.",
                "Intent",
            ),
            factor(
                "Engagement",
                25,
                engagement_value,
                engagement or "No engagement history supplied.",
                "Engagement",
            ),
            factor(
                "Decision readiness",
                20,
                readiness,
                f"Role '{role or 'unknown'}' at stage '{stage}'.",
                "Decision readiness",
            ),
        ]

        score = int(round(sum(item.points for item in factors)))
        score = max(0, min(100, score))
        if score >= self.settings.score_threshold_qualified:
            category = "Qualified"
            band = "high"
            action = "Schedule a discovery conversation and validate the decision process."
        elif score >= self.settings.score_threshold_nurture:
            category = "Nurture"
            band = "medium"
            action = "Collect missing fit and need information before the next outreach."
        else:
            category = "Low priority"
            band = "low"
            action = "Enrich the record or use a lightweight, permissioned nurture touch."

        result = LeadScoreResult(
            score=score,
            qualification_category=category,
            factors=factors,
            positive_signals=[f.explanation for f in factors if f.signal == "positive"],
            negative_signals=[f.explanation for f in factors if f.signal == "negative"],
            missing_information=[f.explanation for f in factors if f.signal == "missing"],
            recommended_next_action=action,
            conversion_probability=None,
            probability_band=band,
        )
        return result, self._execution(started)

    # -- Module 4/6: recommendations and analytics interpretation ---------
    def recommend(self, lead: dict[str, Any]) -> tuple[Recommendation, ExecutionInfo]:
        started = time.perf_counter()
        company = _text(lead.get("company_name")) or "Selected lead"
        engagement = _text(lead.get("engagement_history"))
        needs = _text(lead.get("explicit_needs"))

        evidence: list[EvidenceItem] = []
        if engagement:
            evidence.append(
                EvidenceItem(statement=engagement, source="Lead record", source_type="backend")
            )
        if needs:
            evidence.append(
                EvidenceItem(statement=needs, source="Lead record", source_type="backend")
            )

        if needs and engagement:
            priority, action = "High", "Send a tailored recap and request a discovery meeting."
            timing = "Within one business day"
            channel = "email"
        elif needs or engagement:
            priority, action = "Medium", "Validate the recorded signal and propose a next step."
            timing = "Within three business days"
            channel = "email"
        else:
            priority = "Low"
            action = "Enrich the record before outreach; no verified signal is available."
            timing = None
            # No outreach is justified yet, so no channel is asserted.
            channel = None

        contact = _text(lead.get("contact_name")).split()
        first_name = contact[0] if contact else "there"
        result = Recommendation(
            lead_id=str(lead.get("id")) if lead.get("id") is not None else None,
            related_lead=company,
            recommended_action=action,
            reason=(
                "The lead record contains engagement or a stated need."
                if evidence
                else "No verified interaction or need is recorded, so enrichment should come first."
            ),
            supporting_evidence=evidence,
            priority=priority,
            suggested_timing=timing,
            suggested_channel=channel,
            follow_up_draft=(
                f"Hi {first_name}, thanks for the context. Would it be useful to align on the "
                "next discovery step?"
                if evidence
                else None
            ),
        )
        return result, self._execution(started)

    def interpret_analytics(
        self, analytics: dict[str, Any]
    ) -> tuple[SalesInsightsResult, ExecutionInfo]:
        started = time.perf_counter()
        insights: list[SalesInsight] = []
        pipeline = analytics.get("pipeline_distribution") or []
        if pipeline:
            largest = max(pipeline, key=lambda item: item.get("count", 0))
            insights.append(
                SalesInsight(
                    title="Largest pipeline segment",
                    observation=f"{largest.get('stage')} contains {largest.get('count')} leads.",
                    evidence="Backend-supplied pipeline distribution.",
                    confidence="high",
                )
            )
        trend = analytics.get("activity_trend") or []
        if len(trend) >= 2:
            insights.append(
                SalesInsight(
                    title="Activity movement",
                    observation=(
                        f"Activity changed from {trend[0].get('activity')} to "
                        f"{trend[-1].get('activity')} across the displayed period."
                    ),
                    evidence="Backend-supplied activity trend.",
                    confidence="medium",
                )
            )
        if not insights:
            insights.append(
                SalesInsight(
                    title="Insufficient analytics",
                    observation="No aggregate measures were supplied for trend analysis.",
                    evidence="Empty analytics response.",
                    confidence="low",
                )
            )
        result = SalesInsightsResult(
            insights=insights,
            caveat=(
                "Observations describe supplied aggregates only; they do not establish "
                "causes or forecast results."
            ),
        )
        return result, self._execution(started)
