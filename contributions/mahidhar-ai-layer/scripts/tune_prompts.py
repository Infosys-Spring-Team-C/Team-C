"""Day 14 deliverable — "Tuned prompts" (the prompt half of the task).

Compares every registered prompt variant on two axes:

1. **Structural compliance** — runnable with no API key. Checks each variant's
   render output for the guardrails the Milestone-2 review cares about
   (JSON-only instruction, word-count bound, single CTA, pain-point coverage,
   no-invention clause, owner-attribution rule for summaries).
2. **Live generation** — only if OPENAI_API_KEY is set. Generates the same lead
   across variants, then scores subject length, body length, CTA presence and
   personalisation, and writes the winner to the tuning report.

Usage
-----
    python scripts/tune_prompts.py                 # structural only (offline)
    python scripts/tune_prompts.py --live          # also call the LLM
    python scripts/tune_prompts.py --live --reps 3 # average over 3 draws
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sales_intel.ai.llm.client import get_llm  # noqa: E402
from sales_intel.ai.prompts.registry import (  # noqa: E402
    OUTREACH_VARIANTS,
    SUMMARY_VARIANTS,
    PromptTemplate,
)

OUT_DIR = Path("data/artifacts")

PROSPECT = {
    "company": "Vertex Manufacturing Group",
    "industry": "Manufacturing",
    "persona": "vp",
    "pain_points": "manual lead qualification, slow follow-up, no visibility on pipeline",
    "goal": "book a discovery call",
    "tone": "consultative",
    "length": "short",
    "email_type": "cold_outreach",
}

SUMMARY_ARGS = {
    "interaction_id": "INT-0001",
    "meeting_date": "2026-11-05",
    "internal_speakers": "Priya, Ravi",
    "max_bullets": 6,
    "max_action_items": 10,
    "transcript": (
        "[Priya] Thanks for the time today. We saw your team is evaluating CRM options.\n"
        "[Client] Yes, we're on spreadsheets and it's breaking. We need something by January.\n"
        "[Priya] I'll send a proposal by Friday with the pricing tiers.\n"
        "[Client] Please share the security documentation too. Our CISO will review it.\n"
        "[Client] It's a concern that your integration list is thinner than Salesforce's.\n"
        "[Priya] Understood — we'll line up a technical call next week to walk through the API.\n"
    ),
}

OUTREACH_PAIN = PROSPECT["pain_points"]

# Structural checks: (label, predicate over the rendered user prompt, weight)
OUTREACH_CHECKS: list[tuple[str, callable]] = [
    ("asks for strict JSON output", lambda u, s: "json" in (u + s).lower()),
    ("constrains subject length", lambda u, s: "subject" in u.lower() and ("60" in u or "chars" in u.lower())),
    ("constrains body length", lambda u, s: "words" in u.lower() or "<=" in u),
    ("requires a single CTA", lambda u, s: "call_to_action" in u.lower() or "call-to-action" in u.lower()),
    ("injects the actual pain points", lambda u, s: OUTREACH_PAIN in u),
    ("forbids invented facts/metrics", lambda u, s: "invent" in (u + s).lower() or "cannot prove" in (u + s).lower()),
    ("persona-aware framing", lambda u, s: "persona" in (u + s).lower() or "role" in (u + s).lower()),
    ("names the target stage/goal", lambda u, s: "goal" in (u + s).lower()),
]

SUMMARY_CHECKS: list[tuple[str, callable]] = [
    ("asks for strict JSON output", lambda u, s: "json" in (u + s).lower()),
    ("explicit output schema", lambda u, s: "action_items" in u and "key_discussion_points" in u),
    ("forbids invented owners/dates", lambda u, s: "invent" in (u + s).lower()),
    ("owner attribution rule", lambda u, s: "attribute" in (u + s).lower() or "owner_side" in u),
    ("sentiment per point", lambda u, s: "sentiment" in u.lower()),
    ("injects numeric output bounds", lambda u, s: "max 6" in u.lower() and "max 10" in u.lower()),
    ("internal-speaker awareness", lambda u, s: "internal" in (u + s).lower()),
]


def structural_score(template: PromptTemplate, checks, args) -> dict:
    system, user = template.render(**args)
    passed = [name for name, fn in checks if fn(user, system)]
    failed = [name for name, fn in checks if name not in passed]
    return {
        "variant": template.version,
        "passed": passed,
        "failed": failed,
        "score": round(len(passed) / len(checks), 3),
        "prompt_chars": len(user) + len(system),
    }


def live_outreach(template: PromptTemplate, reps: int) -> dict:
    llm = get_llm()
    results = []
    for _ in range(reps):
        system, user = template.render(**PROSPECT)
        data, resp = llm.chat_json(system, user, temperature=0.4, max_tokens=600)
        subject = str(data.get("subject", ""))
        body = str(data.get("body", ""))
        cta = str(data.get("call_to_action", ""))
        results.append({
            "subject_chars": len(subject),
            "body_words": len(body.split()),
            "has_cta_question": "?" in (cta or body),
            "mentions_pain_point": any(
                p.split()[0].lower() in body.lower() for p in PROSPECT["pain_points"].split(",")
            ),
            "banned_phrases": [
                p for p in ("hope this finds you well", "just following up", "quick question")
                if p in body.lower()
            ],
            "latency_ms": resp.latency_ms,
            "subject": subject,
            "body": body,
        })
    return {
        "variant": template.version,
        "reps": reps,
        "avg_subject_chars": round(sum(r["subject_chars"] for r in results) / reps, 1),
        "avg_body_words": round(sum(r["body_words"] for r in results) / reps, 1),
        "cta_rate": round(sum(r["has_cta_question"] for r in results) / reps, 3),
        "pain_point_rate": round(sum(r["mentions_pain_point"] for r in results) / reps, 3),
        "banned_phrase_hits": sum(len(r["banned_phrases"]) for r in results),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / reps, 1),
        "sample": results[0],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also generate real copy (needs OPENAI_API_KEY)")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "day14_prompt_report.json")
    args = ap.parse_args()

    report: dict = {"outreach_structural": [], "summary_structural": [], "live": []}

    print("== Outreach prompt variants: structural compliance ==")
    for v in OUTREACH_VARIANTS.values():
        r = structural_score(v, OUTREACH_CHECKS, PROSPECT)
        report["outreach_structural"].append(r)
        print(f"  {v.version:>3}  {r['score']:.0%}  failed={r['failed']}")

    print("\n== Summary prompt variants: structural compliance ==")
    for v in SUMMARY_VARIANTS.values():
        r = structural_score(v, SUMMARY_CHECKS, SUMMARY_ARGS)
        report["summary_structural"].append(r)
        print(f"  {v.version:>3}  {r['score']:.0%}  failed={r['failed']}")

    if args.live:
        if not get_llm().available:
            print("\n! --live requested but OPENAI_API_KEY is not set; skipping generation")
        else:
            print(f"\n== Live generation ({args.reps} reps per variant) ==")
            for v in OUTREACH_VARIANTS.values():
                r = live_outreach(v, args.reps)
                report["live"].append(r)
                print(f"  {v.version:>3}  subj={r['avg_subject_chars']:.0f}c "
                      f"body={r['avg_body_words']:.0f}w cta={r['cta_rate']:.0%} "
                      f"pain={r['pain_point_rate']:.0%} banned={r['banned_phrase_hits']} "
                      f"{r['avg_latency_ms']:.0f}ms")

    # Pick the winner: best structural score, then shortest prompt (cheaper).
    best_outreach = max(report["outreach_structural"], key=lambda r: (r["score"], -r["prompt_chars"]))
    best_summary = max(report["summary_structural"], key=lambda r: (r["score"], -r["prompt_chars"]))
    report["selected"] = {"outreach": best_outreach["variant"], "summary": best_summary["variant"]}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nselected outreach prompt : {best_outreach['variant']}")
    print(f"selected summary prompt  : {best_summary['variant']}")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
