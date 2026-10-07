"""Evaluation utilities: discrimination, calibration, thresholded metrics,
bootstrap confidence intervals and subgroup checks.

Censoring note: at horizon k we evaluate only patients whose status at k is known
(event by k, or followed event-free for >= k years). This complete-case approach is
simple but can be biased when censoring depends on risk; inverse-probability-of-
censoring weighting (IPCW) is listed as future work. In this simulator censoring is
independent of risk, so the bias is expected to be small.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 10):
    order = np.argsort(p)
    bins = np.array_split(order, n_bins)
    out = []
    for b in bins:
        if len(b):
            out.append({"mean_predicted": float(p[b].mean()), "observed_rate": float(y[b].mean()),
                        "n": int(len(b))})
    return out


def ece(y, p, n_bins: int = 10) -> float:
    bins = calibration_bins(y, p, n_bins)
    n = sum(b["n"] for b in bins)
    return float(sum(b["n"] / n * abs(b["mean_predicted"] - b["observed_rate"]) for b in bins))


def calibration_slope_intercept(y, p):
    """Logistic recalibration: logit(P(y=1)) = a + b * logit(p)."""
    from sklearn.linear_model import LogisticRegression
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    m = LogisticRegression(C=1e6, max_iter=1000).fit(lp.reshape(-1, 1), y)
    return float(m.intercept_[0]), float(m.coef_[0][0])


def youden_threshold(y, p) -> float:
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(y, p)
    ok = np.isfinite(thr)  # sklearn prepends +inf as the "predict nothing" threshold
    return float(np.clip(thr[ok][np.argmax((tpr - fpr)[ok])], 0.0, 1.0))


def threshold_metrics(y, p, thr):
    pred = (p >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    return {
        "threshold": float(thr),
        "sensitivity": tp / max(tp + fn, 1), "specificity": tn / max(tn + fp, 1),
        "ppv": tp / max(tp + fp, 1), "npv": tn / max(tn + fn, 1),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def bootstrap_ci(y, p, fn, n: int = 200, seed: int = 0):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        vals.append(fn(y[i], p[i]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def evaluate_binary(y, p, thr, n_boot=200, seed=0):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    res = {
        "n": int(len(y)), "events": int(y.sum()), "prevalence": float(y.mean()),
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
        "mean_predicted": float(p.mean()),
    }
    res["auroc_ci"] = bootstrap_ci(y, p, roc_auc_score, n_boot, seed)
    res["auprc_ci"] = bootstrap_ci(y, p, average_precision_score, n_boot, seed)
    res["brier_ci"] = bootstrap_ci(y, p, brier_score_loss, n_boot, seed)
    a, b = calibration_slope_intercept(y, p)
    res["calibration_intercept"], res["calibration_slope"] = a, b
    res["calibration_bins"] = calibration_bins(y, p)
    res.update(threshold_metrics(y, p, thr))
    return res
