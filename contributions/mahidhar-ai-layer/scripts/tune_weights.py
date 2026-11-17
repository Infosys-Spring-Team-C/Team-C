"""Day 14 deliverable — "Tuned prompts and weights".

Usage
-----
    python scripts/tune_weights.py --seed 42
    python scripts/tune_weights.py --dataset data/sample/leads_labelled.json
    python scripts/tune_prompts.py            # prompt A/B side-by-side

Outputs
-------
    data/artifacts/scoring_weights.json      <- loaded automatically at runtime
    data/artifacts/day14_tuning_report.md    <- paste into the tuning report
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sales_intel.ai.scoring.engine import dimension_subscores, load_scoring_config  # noqa: E402
from sales_intel.ai.scoring.tuner import (  # noqa: E402
    Candidate,
    ScoringTuner,
    write_artifacts,
)
from sales_intel.config import DEFAULT_SCORING, WEIGHTS_FILE  # noqa: E402
from sales_intel.schemas import LeadFeatures  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

DEFAULT_DATASET = Path("data/sample/leads_labelled.json")


def load_dataset(path: Path) -> tuple[list[LeadFeatures], list[int]]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    leads, labels = [], []
    for row in rows:
        label = int(row.pop("converted"))
        leads.append(LeadFeatures(**row))
        labels.append(label)
    return leads, labels


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune lead-scoring weights (Day 14)")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out", type=Path, default=WEIGHTS_FILE)
    ap.add_argument("--target", type=float, default=DEFAULT_SCORING["min_accuracy_target"])
    args = ap.parse_args()

    if not args.dataset.exists():
        print(f"dataset not found: {args.dataset}\n"
              f"generate one with: python scripts/generate_sample_data.py")
        return 2

    leads, labels = load_dataset(args.dataset)
    positives = sum(labels)
    logging.info("loaded %s leads (%s converted / %s not)", len(leads), positives, len(leads) - positives)

    tuner = ScoringTuner(leads, labels, n_trials=args.trials, folds=args.folds, seed=args.seed)

    # Baseline = the hard-coded defaults, evaluated through the exact same CV.
    baseline_cand = Candidate(
        weights=dict(DEFAULT_SCORING["weights"]),
        logistic_a=DEFAULT_SCORING["logistic_a"],
        logistic_b=DEFAULT_SCORING["logistic_b"],
    )
    baseline = tuner.cross_validate(baseline_cand)
    logging.info("baseline: acc=%.2f%% auc=%.4f", baseline.accuracy * 100, baseline.auc)

    best = tuner.run()
    payload = write_artifacts(best, baseline, out_path=args.out, target=args.target)

    print("\n=== Day 14 tuning result ===")
    print(f"target accuracy : {args.target:.0%}")
    print(f"baseline        : {baseline.accuracy:.2%} (AUC {baseline.auc:.4f})")
    print(f"tuned           : {best.accuracy:.2%} (AUC {best.auc:.4f})  "
          f"{'PASS' if payload['metrics']['target_met'] else 'BELOW TARGET'}")
    print(f"weights         : {best.weights}")
    print(f"logistic        : a={best.logistic_a} b={best.logistic_b}")
    print(f"written         : {args.out} + report next to it")

    # Sanity check: the tuned config must load back through the production path.
    cfg = load_scoring_config(args.out)
    assert cfg["model_version"].startswith("m2-scoring"), cfg["model_version"]
    sample = dimension_subscores(leads[0])
    print(f"reload check    : model={cfg['model_version']} subscores={sample}")
    return 0 if payload["metrics"]["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
