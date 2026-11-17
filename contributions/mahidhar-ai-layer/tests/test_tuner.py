"""Tests for the Day-14 weight tuner: metric correctness + learning behaviour."""
from __future__ import annotations

import json

import pytest

from sales_intel.ai.scoring.tuner import (
    Candidate,
    ScoringTuner,
    accuracy,
    log_loss,
    roc_auc,
    stratified_folds,
    write_artifacts,
)
from sales_intel.config import DEFAULT_SCORING


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def test_roc_auc_perfect_and_chance():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0
    assert roc_auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_roc_auc_handles_ties():
    # One positive tied with one negative -> average rank gives 0.5 contribution
    auc = roc_auc([0, 1], [0.4, 0.4])
    assert auc == 0.5


def test_roc_auc_single_class_is_neutral():
    assert roc_auc([1, 1, 1], [0.1, 0.5, 0.9]) == 0.5


def test_accuracy_and_logloss():
    assert accuracy([1, 0, 1, 0], [1, 0, 1, 1]) == 0.75
    assert log_loss([1, 0], [0.9, 0.1]) < log_loss([1, 0], [0.5, 0.5])
    assert accuracy([], []) == 0.0


def test_stratified_folds_are_balanced_and_disjoint():
    y = [1] * 20 + [0] * 30
    folds = stratified_folds(y, k=5, seed=42)
    flat = sorted(i for f in folds for i in f)
    assert flat == list(range(50))                     # every index exactly once
    for f in folds:
        pos = sum(y[i] for i in f)
        assert 3 <= pos <= 5                            # 20/5 = 4 positives per fold
    assert len({tuple(f) for f in folds}) == 5


# ---------------------------------------------------------------------------
# Tuner behaviour
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_tuner_improves_on_baseline(labelled_leads):
    leads, labels = labelled_leads
    tuner = ScoringTuner(leads, labels, n_trials=60, seed=42)
    baseline = tuner.cross_validate(Candidate(
        weights=dict(DEFAULT_SCORING["weights"]),
        logistic_a=DEFAULT_SCORING["logistic_a"],
        logistic_b=DEFAULT_SCORING["logistic_b"],
    ))
    best = tuner.run()
    assert best.accuracy >= baseline.accuracy
    assert best.auc >= 0.75
    assert abs(sum(best.weights.values()) - 1.0) < 1e-6
    assert all(v >= 0 for v in best.weights.values())


@pytest.mark.slow
def test_tuner_respects_accuracy_target(labelled_leads):
    leads, labels = labelled_leads
    tuner = ScoringTuner(leads, labels, n_trials=120, seed=42)
    best = tuner.run()
    assert best.accuracy >= DEFAULT_SCORING["min_accuracy_target"], (
        f"tuned accuracy {best.accuracy:.2%} below the 85% Milestone-2 target"
    )


def test_tuner_rejects_tiny_datasets(hot_lead):
    with pytest.raises(ValueError, match="at least"):
        ScoringTuner([hot_lead] * 2, [0, 1], folds=5)


def test_tuner_rejects_mismatched_lengths(labelled_leads):
    leads, labels = labelled_leads
    with pytest.raises(ValueError, match="same length"):
        ScoringTuner(leads[:10], labels[:5])


def test_write_artifacts_produces_loadable_config(tmp_path, labelled_leads):
    leads, labels = labelled_leads
    tuner = ScoringTuner(leads, labels, n_trials=40, seed=7)
    best = tuner.run()
    base = tuner.cross_validate(Candidate(
        weights=dict(DEFAULT_SCORING["weights"]),
        logistic_a=DEFAULT_SCORING["logistic_a"],
        logistic_b=DEFAULT_SCORING["logistic_b"],
    ))
    out = tmp_path / "weights.json"
    payload = write_artifacts(best, base, out_path=out, target=0.85)

    assert out.exists()
    assert (tmp_path / "day14_tuning_report.md").exists()
    assert json.loads(out.read_text())["weights"].keys() == {
        "engagement", "fit", "intent", "decision_readiness"
    }
    assert "accuracy" in payload["metrics"]
    assert "target_met" in payload["metrics"]

    from sales_intel.ai.scoring.engine import load_scoring_config

    cfg = load_scoring_config(out)
    assert cfg["model_version"] == "m2-scoring-v1"
