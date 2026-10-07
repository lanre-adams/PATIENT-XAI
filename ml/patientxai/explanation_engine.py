"""Explanation Engine: deterministic, template-based technical and plain-language
explanations generated after every prediction.

Deliberately NOT a language model: every sentence is traceable to a computed
quantity, wording is reviewable, and the engine cannot invent clinical advice.
The plain-language text separates five ideas that are easy to conflate:
prediction, association, uncertainty, counterfactual simulation and causality.
"""

from __future__ import annotations

from . import COUNTERFACTUAL_CAVEAT, DISCLAIMER

# Phrases the engine must never emit (checked by tests).
FORBIDDEN = ["you should", "we recommend", "recommended treatment", "start taking", "stop taking",
             "prescribe", "diagnos", "consult your doctor to change"]


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _band(r: float) -> str:
    if r < 0.10:
        return "lower"
    if r < 0.20:
        return "intermediate"
    return "elevated"


def technical(prediction: dict, explanation: dict, counterfactual: dict | None,
              performance: dict | None, n_visits: int, span_years: float) -> list[str]:
    h = prediction["primary_horizon"]
    i = prediction["horizons_years"].index(h)
    lines = [
        f"Model: {prediction['model_name']} (model key '{prediction['model']}').",
        f"Estimated {h}-year cumulative risk: {prediction['risk'][i]:.3f} "
        f"(member spread {prediction['lower'][i]:.3f}-{prediction['upper'][i]:.3f}; "
        f"{prediction['uncertainty_method']}; n={prediction['n_members']}).",
        "Risk trajectory (years 1-5): " + ", ".join(f"{r:.3f}" for r in prediction["risk"]) + ".",
        f"Temporal context: {n_visits} synthetic visits spanning {span_years:.1f} years before the index visit.",
        f"Attribution method: {explanation['method']}; units: {explanation['units']}.",
    ]
    top = explanation["contributions"][:5]
    lines.append("Largest contributions: " + "; ".join(
        f"{c['label']} {c['contribution']:+.4f}" for c in top) + ".")
    if explanation.get("completeness"):
        c = explanation["completeness"]
        lines.append(f"IG completeness check: sum of attributions {c['sum_attributions']:+.4f} vs "
                     f"f(x)-f(baseline) {c['f_x_minus_f_baseline']:+.4f} (gap {c['gap']:.4f}).")
    if explanation.get("temporal"):
        t = max(explanation["temporal"], key=lambda r: r["share"])
        lines.append(f"Most influential visit: #{t['visit_index'] + 1} ({t['visit_date']}), "
                     f"{100 * t['share']:.0f}% of total absolute attribution.")
    if counterfactual:
        d = counterfactual["difference"][i]
        lines.append(f"Counterfactual simulation ({', '.join(c['label'] for c in counterfactual['changed'])}): "
                     f"{h}-year risk {counterfactual['baseline_risk'][i]:.3f} -> "
                     f"{counterfactual['counterfactual_risk'][i]:.3f} (difference {d:+.3f}, paired member "
                     f"range {counterfactual['difference_lower'][i]:+.3f} to {counterfactual['difference_upper'][i]:+.3f}).")
    if performance:
        m = performance["models"].get(prediction["model"], {}).get("by_horizon", {}).get(str(h))
        if m:
            lines.append(f"Calibration caveat: on the synthetic temporal test cohort this model has calibration "
                         f"slope {m['calibration_slope']:.2f}, intercept {m['calibration_intercept']:+.2f}, "
                         f"ECE {m['ece']:.3f}. Cohort-level calibration does not guarantee calibration for "
                         f"an individual or a subgroup.")
    lines.append("Attributions describe the model's computation, not mechanisms in the data-generating process.")
    return lines


def plain_language(prediction: dict, explanation: dict, counterfactual: dict | None) -> dict:
    h = prediction["primary_horizon"]
    i = prediction["horizons_years"].index(h)
    r, lo, hi = prediction["risk"][i], prediction["lower"][i], prediction["upper"][i]
    ups = [c["label"] for c in explanation["contributions"] if c["contribution"] > 0][:3]
    downs = [c["label"] for c in explanation["contributions"] if c["contribution"] < 0][:2]
    out = {
        "prediction": (f"For this synthetic profile, the model estimated {'an' if _band(r)[0] in 'aeiou' else 'a'} "
                       f"{_band(r)} chance "
                       f"({_pct(r)}) of the synthetic outcome within {h} years. This is a statistical "
                       f"estimate for a simulated record, not a statement about any real person."),
        "association": (("The measurements that pushed the estimate up most were "
                         + ", ".join(ups) + ". ") if ups else "")
        + (("Measurements that pulled it down included " + ", ".join(downs) + ". ") if downs else "")
        + "These are associations the model learned from synthetic data. They should not be "
          "interpreted as clinical causes.",
        "uncertainty": (f"Different versions of the model gave estimates between {_pct(lo)} and {_pct(hi)}. "
                        "A wide range means the model is less certain. Even a narrow range only reflects "
                        "disagreement between model versions, not every source of error."),
        "counterfactual": None,
        "causality": ("A prediction model learns patterns, not cause and effect. Some measurements, such as "
                      "being on a medication, can look linked to higher risk simply because they are given to "
                      "people who were already at higher risk."),
        "disclaimer": DISCLAIMER,
    }
    if counterfactual:
        d = counterfactual["difference"][i]
        what = ", ".join(f"{c['label']} from {c['from']} to {c['to']}" for c in counterfactual["changed"])
        direction = "lower" if d < 0 else "higher"
        out["counterfactual"] = (f"In a 'what-if' simulation that changed {what}, the model's estimate became "
                                 f"{_pct(counterfactual['counterfactual_risk'][i])}, which is {abs(100 * d):.1f} "
                                 f"percentage points {direction}. " + COUNTERFACTUAL_CAVEAT)
    return out


def generate(prediction, explanation, counterfactual=None, performance=None, n_visits=0, span_years=0.0):
    return {"technical": technical(prediction, explanation, counterfactual, performance, n_visits, span_years),
            "plain_language": plain_language(prediction, explanation, counterfactual)}


def contains_forbidden(text: str) -> list[str]:
    t = text.lower()
    return [f for f in FORBIDDEN if f in t]
