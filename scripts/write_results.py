"""Write docs/results.md from the saved artifacts, so reported numbers always match the run."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from patientxai.config import PipelineConfig  # noqa: E402


def pts(x):
    return f"{100 * x:+.1f} pts"


def main():
    art = PipelineConfig().artifacts_dir
    perf = json.loads((art / "performance.json").read_text())
    audit = json.loads((art / "counterfactual_audit.json").read_text())
    man = json.loads((art / "manifest.json").read_text())
    h = str(perf["primary_horizon"])
    L = ["# Results (generated)", "",
         f"Generated from `artifacts/` by `scripts/write_results.py`. Run created {man['created_utc']}, "
         f"model version `{man['model_version']}`, pipeline runtime {man['runtime_seconds']} s. "
         f"Data hash (visits) `{man['data_sha256_16']['visits']}`.", "",
         "**All results are on SYNTHETIC data from a known simulator. They demonstrate the pipeline, "
         "not clinical performance.**", "", "## Cohort", "",
         "| Split | Enrolment years | Patients | Observed events | Known status at 3 y |", "|---|---|---|---|---|"]
    for k, v in perf["cohort"].items():
        L.append(f"| {k} | {', '.join(map(str, v['enrolment_years']))} | {v['patients']} | {v['events_observed']} | "
                 f"{v['known_status_at_primary_horizon']} |")
    L += ["", f"## Test-cohort performance at {h} years", "",
          "| Model | AUROC (95% CI) | AUPRC (95% CI) | Brier | ECE | Cal. slope | Cal. intercept | Sens. | Spec. |",
          "|---|---|---|---|---|---|---|---|---|"]
    for _k, m in perf["models"].items():
        r = m["by_horizon"][h]
        L.append(f"| {m['name']} | {r['auroc']:.3f} ({r['auroc_ci'][0]:.3f}–{r['auroc_ci'][1]:.3f}) | "
                 f"{r['auprc']:.3f} ({r['auprc_ci'][0]:.3f}–{r['auprc_ci'][1]:.3f}) | {r['brier']:.3f} | {r['ece']:.3f} | "
                 f"{r['calibration_slope']:.2f} | {r['calibration_intercept']:+.2f} | {r['sensitivity']:.2f} | "
                 f"{r['specificity']:.2f} |")
    L += ["", "AUROC by horizon (years 1–5):", ""]
    for _k, m in perf["models"].items():
        L.append(f"- {m['name']}: " + ", ".join(f"{hh}y {r['auroc']:.3f}" for hh, r in m["by_horizon"].items()))
    L += ["", "## Subgroups (sex), 3-year horizon", "", "| Model | Group | n | Observed | Mean predicted | AUROC |",
          "|---|---|---|---|---|---|"]
    for _k, m in perf["models"].items():
        for g, r in m["subgroups_sex"].items():
            L.append(f"| {m['name']} | {g} | {r['n']} | {r['prevalence']:.3f} | {r['mean_predicted']:.3f} | {r['auroc']:.3f} |")
    L += ["", f"## Counterfactual audit ({audit['horizon_years']}-year risk, {audit['n_sampled_test_patients']} "
          "sampled test patients)", "",
          "| Intervention | n | Causal in simulator | True mean change | GRU simulated | Baseline simulated | GRU–truth r | Sign agreement |",
          "|---|---|---|---|---|---|---|---|"]
    for k, v in audit["interventions"].items():
        r = "n/a" if v["gru_corr_with_truth"] is None else f"{v['gru_corr_with_truth']:.2f}"
        s = "n/a" if v["gru_sign_agreement"] is None else f"{100 * v['gru_sign_agreement']:.0f}%"
        L.append(f"| {k} | {v['n']} | {'yes' if v['causal_in_simulator'] else 'no (marker)'} | "
                 f"{pts(v['true_mean_change'])} | {pts(v['gru_mean_change'])} | {pts(v['baseline_mean_change'])} | {r} | {s} |")
    (ROOT / "docs" / "results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
