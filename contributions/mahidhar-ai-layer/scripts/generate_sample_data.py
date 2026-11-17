"""Generate the Day-6 "sample lead dataset" plus labelled data for Day-14 tuning.

Ground-truth model
------------------
A single latent *propensity* per account drives everything. Four observed
dimensions are noisy proxies of it, and the outcome is a Bernoulli draw from a
logistic on a weighted signal:

    signal  = 0.09*engagement + 0.16*fit + 0.36*intent + 0.39*decision_readiness
    logit   = bias + separation * (signal - 0.5) + N(0, label_noise)
    convert ~ Bernoulli(sigmoid(logit))

Two properties are deliberate, because they are what make the Day-14 tuning
honest rather than circular:

* **engagement is the weakest predictor** (opens and clicks are cheap signals),
  which is exactly why the tuned weights should not match the naive defaults;
* `--separation` controls how far apart converters and non-converters sit. Its
  default (11) puts the *oracle ceiling* near 88% accuracy — so the Milestone-2
  "85% or more" target is reachable but not free. Lower it and even a perfect
  model cannot clear 85%: that ceiling is a property of Bernoulli label noise,
  not of the model. `--report-ceiling` prints it.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

INDUSTRIES = ["SaaS", "Manufacturing", "BFSI", "Healthcare", "Retail", "Logistics"]
TRUTH_WEIGHTS = {"engagement": 0.09, "fit": 0.16, "intent": 0.36, "decision_readiness": 0.39}
COMPANY_A = ["North", "Vertex", "Orbit", "Keystone", "BlueRiver", "Apex", "Zenith", "Falcon", "Titan", "Lumen"]
COMPANY_B = ["Labs", "Group", "Systems", "Partners", "Industries", "Technologies"]


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def make_lead(
    rng: random.Random,
    idx: int,
    feature_noise: float = 0.12,
    label_noise: float = 0.25,
    separation: float = 11.0,
    bias: float = -0.9,
) -> tuple[dict, int, float]:
    industry = rng.choice(INDUSTRIES)
    propensity = rng.betavariate(1.35, 1.35)

    def noisy(spread: float) -> float:
        return max(0.0, min(1.0, propensity + rng.gauss(0, spread)))

    # engagement is intentionally noisier than intent/readiness
    eng = noisy(feature_noise * 1.5)
    fit = noisy(feature_noise * 1.5)
    intent = noisy(feature_noise)
    readiness = noisy(feature_noise)

    lead = {
        "lead_id": f"L{idx:04d}",
        "company_name": f"{rng.choice(COMPANY_A)} {industry} {rng.choice(COMPANY_B)}",
        "industry": industry,
        # engagement (weakest signal, noisiest)
        "email_opens": int(round(eng * 16)),
        "email_clicks": int(round(eng * 6)),
        "email_replies": int(round(eng * 4)),
        "inbound_replies": int(round(eng * eng * 4)),
        "meetings_held": int(round(eng * 3)),
        "call_connect_rate": round(min(0.85, eng * 0.75 + rng.uniform(0, 0.08)), 2),
        "avg_response_latency_hours": round(max(1.0, (1 - eng) * 70 + rng.uniform(-4, 6)), 1),
        # fit
        "industry_match": round(min(1.0, fit + rng.uniform(-0.10, 0.12)), 2),
        "company_size_score": round(min(1.0, fit), 2),
        "seniority_score": round(min(1.0, readiness + rng.uniform(-0.08, 0.10)), 2),
        "tech_stack_overlap": round(min(1.0, fit + rng.uniform(-0.12, 0.10)), 2),
        "budget_potential_usd": int(5_000 + fit * 150_000 * rng.uniform(0.6, 1.5)),
        # intent (strong signal)
        "pricing_page_visits": int(round(intent * 8)),
        "demo_requests": int(round(intent * 2.6)),
        "content_downloads": int(round(intent * 5)),
        "hiring_signal": int(round(intent * 3)),
        "competitor_mention": int(round(intent * 2)),
        # decision readiness (strong signal)
        "budget_confirmed": 1 if readiness > 0.45 else 0,
        "timeline_months": int(round(max(1, 15 - readiness * 13))),
        "stakeholders_identified": int(round(readiness * 4.6)),
        "procurement_stage": min(3, int(round(readiness * 3.3))),
        "champion_identified": 1 if readiness > 0.5 else 0,
    }

    signal = (
        TRUTH_WEIGHTS["engagement"] * eng
        + TRUTH_WEIGHTS["fit"] * fit
        + TRUTH_WEIGHTS["intent"] * intent
        + TRUTH_WEIGHTS["decision_readiness"] * readiness
    )
    logit = bias + separation * (signal - 0.5) + rng.gauss(0, label_noise)
    return lead, int(rng.random() < sigmoid(logit)), signal


def oracle_ceiling(rows: list[tuple[int, float]]) -> tuple[float, float]:
    """Best achievable accuracy from the latent signal alone (upper bound)."""
    best_acc, best_t = 0.0, 0.0
    for i in range(10, 95):
        t = i / 1.0
        acc = sum(int((s * 100 >= t) == bool(y)) for y, s in rows) / len(rows)
        if acc > best_acc:
            best_acc, best_t = acc, t
    return best_acc, best_t


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic labelled lead data")
    ap.add_argument("-n", "--count", type=int, default=320)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--feature-noise", type=float, default=0.12)
    ap.add_argument("--label-noise", type=float, default=0.25)
    ap.add_argument("--separation", type=float, default=11.0,
                    help="signal strength; 11 ~ 88%% oracle accuracy ceiling")
    ap.add_argument("--bias", type=float, default=-0.9, help="shifts the base rate")
    ap.add_argument("--out", type=Path, default=Path("data/sample/leads_labelled.json"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    generated = [
        make_lead(rng, i + 1, args.feature_noise, args.label_noise, args.separation, args.bias)
        for i in range(args.count)
    ]
    payload = [{"converted": c, **lead} for lead, c, _ in generated]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    pos = sum(p["converted"] for p in payload)
    print(f"wrote {len(payload)} leads to {args.out}")
    print(f"  base rate          : {pos}/{len(payload)} converted ({pos / len(payload):.1%})")
    ceiling, thr = oracle_ceiling([(c, s) for _, c, s in generated])
    print(f"  oracle ceiling     : {ceiling:.2%} accuracy (threshold {thr:.0f}) "
          f"— the tuner cannot beat this")
    print(f"  target             : 85.0%  -> "
          f"{'achievable' if ceiling >= 0.85 else 'NOT achievable, lower --label-noise or raise --separation'}")

    raw = [{k: v for k, v in p.items() if k != "converted"} for p in payload[:40]]
    batch_path = args.out.parent / "leads_batch_40.json"
    batch_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"  unlabelled batch   : {batch_path} ({len(raw)} leads)")


if __name__ == "__main__":
    main()
