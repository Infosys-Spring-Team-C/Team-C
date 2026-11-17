"""Headless demo of the three AI/ML services — no UI required.

Runs in a terminal, a CI job or a demo box with no browser — no UI dependency.

Usage
-----
    python scripts/run_ai_demo.py                 # all three services
    python scripts/run_ai_demo.py --task score    # lead scoring only
    python scripts/run_ai_demo.py --task nba      # next-best-action only
    python scripts/run_ai_demo.py --task summary  # summarisation only
    python scripts/run_ai_demo.py --lead L0007    # pick a lead from the sample set
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sales_intel.ai.nba.engine import recommend
from sales_intel.ai.scoring.engine import load_scoring_config, score_lead
from sales_intel.ai.prompts.registry import DEFAULT_SUMMARY, DEFAULT_OUTREACH
from sales_intel.ai.summarization.engine import summarise, to_interaction_record
from sales_intel.config import NBA_CONFIG, SUMMARY_CONFIG
from sales_intel.schemas import LeadContext, LeadFeatures, Utterance

SAMPLE = Path("data/sample")
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def rule(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}\n" + "─" * min(len(title) + 4, 78))


def load_lead(lead_id: str | None) -> LeadFeatures:
    path = SAMPLE / "leads_batch_40.json"
    if not path.exists():
        print("sample data missing — run: python scripts/generate_sample_data.py")
        raise SystemExit(2)
    rows = json.loads(path.read_text(encoding="utf-8"))
    if lead_id:
        rows = [r for r in rows if r["lead_id"] == lead_id]
        if not rows:
            raise SystemExit(f"lead {lead_id} not found in {path}")
    return LeadFeatures(**rows[0])


def demo_score(lead: LeadFeatures, cfg: dict) -> None:
    rule("DAY 12/14 — LEAD SCORING")
    started = time.perf_counter()
    result = score_lead(lead, cfg)
    ms = (time.perf_counter() - started) * 1000

    print(f"lead            : {lead.lead_id} · {lead.company_name} ({lead.industry})")
    print(f"score           : {BOLD}{result.score:.1f}/100{RESET}  [{result.band}]")
    print(f"P(convert)      : {result.conversion_probability:.0%}")
    print(f"model           : {result.model_version}  ({ms:.2f} ms)")
    print("\nsubscores (weight → points contributed):")
    for d in result.drivers:
        bar = "█" * max(1, int(d["subscore"] / 5))
        print(f"  {d['dimension']:<19} {d['subscore']:>6.1f}  ×{d['weight']:.2f} = "
              f"{d['contribution']:>5.1f} pts  {DIM}{bar}{RESET}")


def demo_nba(lead: LeadFeatures, cfg: dict) -> None:
    rule("DAY 15 — NEXT BEST ACTION")
    ctx = LeadContext(
        lead_id=lead.lead_id,
        company_name=lead.company_name,
        industry=lead.industry,
        lifecycle_stage="qualified",
        seniority="vp",
        decision_maker=True,
        deal_value_usd=lead.budget_potential_usd,
        last_contact_at=datetime.now() - timedelta(days=5),
        local_hour=11,
        pain_points=["manual lead qualification", "slow follow-up"],
    )
    nba = recommend(lead, ctx, today=date.today(), scoring_config=cfg)

    print(f"priority        : {BOLD}{nba.priority}{RESET} ({nba.priority_score:.0f}/100)")
    print(f"next touch      : {nba.next_touch_date:%a, %d %b %Y} via {nba.recommended_channel}")
    print(f"days since touch: {nba.days_since_last_contact}")
    if nba.suppress:
        print(f"\n⛔ SUPPRESSED — {nba.suppress_reason}")

    print("\nfollow-up cadence:")
    for t in nba.cadence:
        print(f"  {t.step}. {t.planned_at:%a %d %b}  {t.channel:<9} {t.purpose}")

    print("\nchannel mix:")
    for c in nba.channel_mix:
        print(f"  {c.channel:<9} {c.share:>3}%  {DIM}{c.rationale}{RESET}")

    print("\ncontent strategy:")
    print(f"  type  : {nba.content.content_type}")
    print(f"  angle : {nba.content.angle}")
    print(f"  asset : {nba.content.suggested_asset}")
    print(f"  CTA   : {nba.content.call_to_action}")
    for m in nba.content.key_messages[:3]:
        print(f"  • {m}")

    print("\nwhy:")
    for r in nba.rationale:
        print(f"  - {r}")
    if nba.risk_flags:
        print("\nrisk flags:")
        for f in nba.risk_flags:
            print(f"  ! {f}")

    cap = NBA_CONFIG["max_touches_per_14_days"][nba.priority]
    print(f"\n{DIM}guardrail: max {cap} touches / 14 days at {nba.priority}{RESET}")


def demo_summary() -> None:
    rule("DAY 24 — CONVERSATION SUMMARISATION")
    path = SAMPLE / "transcripts.json"
    if not path.exists():
        print("no transcripts — add data/sample/transcripts.json")
        return
    transcripts = json.loads(path.read_text(encoding="utf-8"))
    name = next(iter(transcripts))
    text = transcripts[name]

    utterances = []
    for line in text.splitlines():
        speaker, _, body = line.partition(":")
        if body.strip():
            utterances.append(Utterance(speaker=speaker.strip(), text=body.strip()))

    started = time.perf_counter()
    summary = summarise(
        utterances, interaction_id="INT-DEMO-001", lead_id="L-DEMO", meeting_date=date.today()
    )
    ms = (time.perf_counter() - started) * 1000

    print(f"transcript      : {name}")
    print(f"turns           : {len(utterances)}  |  engine: {summary.engine} "
          f"({summary.model})  |  {ms:.2f} ms")
    print(f"confidence      : {summary.confidence:.0%}  |  sentiment: {summary.overall_sentiment}  "
          f"|  internal talk: {summary.talk_ratio_internal:.0%}")
    print(f"\n{BOLD}summary{RESET}\n  {summary.summary}")

    print(f"\n{BOLD}key discussion points{RESET}")
    for p in summary.key_discussion_points:
        print(f"  [{p.sentiment:<8}] {p.topic:<15} “{p.quote[:88]}”")

    print(f"\n{BOLD}action items{RESET}")
    for a in summary.action_items:
        due = a.due_date.strftime("%d %b") if a.due_date else "—"
        print(f"  {a.priority:<6} {due:<7} {a.owner}/{a.owner_side:<8} {a.task[:70]}")

    if summary.decisions:
        print(f"\n{BOLD}decisions{RESET}")
        for d in summary.decisions:
            print(f"  - {d}")
    if summary.objections:
        print(f"\n{BOLD}objections{RESET}")
        for o in summary.objections:
            print(f"  - {o}")
    if summary.competitors_mentioned:
        print(f"\ncompetitors     : {', '.join(summary.competitors_mentioned)}")
    print(f"next step       : {summary.next_step}")

    record = to_interaction_record(summary)
    print(f"\n{DIM}Sales_Interactions payload: {len(record)} fields "
          f"({record['open_action_count']} open actions, "
          f"{record['high_priority_count']} high priority){RESET}")
    print(f"{DIM}prompt: {DEFAULT_SUMMARY.id} {DEFAULT_SUMMARY.version} · caps: "
          f"{SUMMARY_CONFIG['max_bullets']} points / {SUMMARY_CONFIG['max_action_items']} actions{RESET}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless demo of the AI/ML layer")
    ap.add_argument("--task", choices=["all", "score", "nba", "summary"], default="all")
    ap.add_argument("--lead", help="lead id from data/sample/leads_batch_40.json")
    args = ap.parse_args()

    cfg = load_scoring_config()
    if args.task in {"all", "score", "nba"}:
        lead = load_lead(args.lead)
    if args.task in {"all", "score"}:
        demo_score(lead, cfg)
    if args.task in {"all", "nba"}:
        demo_nba(lead, cfg)
    if args.task in {"all", "summary"}:
        demo_summary()
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
