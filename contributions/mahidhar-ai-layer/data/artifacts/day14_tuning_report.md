# Day 14 — Scoring Weight Tuning Report

**Target:** accuracy >= 85%  |  **Result:** 89.06% — **PASS**

| Metric | Baseline (defaults) | Tuned |
|---|---|---|
| Accuracy | 84.38% | **89.06%** |
| ROC-AUC | 0.9364 | **0.9401** |
| Log-loss | 0.3365 | 0.3069 |
| Objective (0.5*acc + 0.5*auc) | 0.8901 | 0.9154 |

## Shipped weights (`m2-scoring-v1`)

| Dimension | Baseline | Tuned | Δ |
|---|---|---|---|
| engagement | 0.30 | 0.15 | -0.15 |
| fit | 0.25 | 0.24 | -0.01 |
| intent | 0.25 | 0.43 | +0.18 |
| decision_readiness | 0.20 | 0.17 | -0.03 |

Logistic calibration: a = 0.12, b = 62.5
(probability = 1 / (1 + e^(-a·(score - b))))

## Notes for the Milestone-2 review
- Weights constrained to the simplex (non-negative, sum = 1.0) so scores stay
  comparable across model versions.
- Accuracy/AUC are **5-fold stratified cross-validated**, not in-sample.
- Tuning is seeded and reproducible: `python scripts/tune_weights.py --seed 42`.
