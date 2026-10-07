"""Trustworthy AI Report: a structured, exportable record of one prediction."""

from __future__ import annotations

import html
import io
from datetime import datetime, timezone

from . import COUNTERFACTUAL_CAVEAT, DISCLAIMER, MODEL_VERSION

KNOWN_LIMITATIONS = [
    "Trained and evaluated only on SYNTHETIC data from a known simulator; performance says nothing about real patients.",
    "Not clinically validated; no external validation; not a medical device; no regulatory approval.",
    "Attributions explain the model's computation and are not causal explanations.",
    "Counterfactual results are model-based simulations; in this simulator they can disagree in size and even "
    "direction with the true interventional effect (see the counterfactual audit).",
    "Uncertainty reflects ensemble/bootstrap disagreement only; it omits data, label and shift uncertainty.",
    "Complete-case evaluation at each horizon (no inverse-probability-of-censoring weighting).",
    "Synthetic imaging embeddings stand in for a real image encoder.",
]


def build_report(patient_id, prediction, explanation, narrative, counterfactual, performance, dataset_type):
    h = prediction["primary_horizon"]
    i = prediction["horizons_years"].index(h)
    perf = performance["models"].get(prediction["model"], {}).get("by_horizon", {}).get(str(h), {})
    return {
        "title": "PATIENT-XAI Trustworthy AI Report",
        "disclaimer": DISCLAIMER,
        "patient_id": patient_id,
        "dataset_type": dataset_type,
        "model": prediction["model_name"],
        "model_version": MODEL_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prediction": {"horizon_years": h, "risk": prediction["risk"][i], "trajectory": prediction["risk"]},
        "uncertainty": {"lower": prediction["lower"][i], "upper": prediction["upper"][i],
                        "method": prediction["uncertainty_method"]},
        "important_features": [{"label": c["label"], "contribution": c["contribution"]}
                               for c in explanation["contributions"][:6]],
        "attribution_method": explanation["method"], "attribution_units": explanation["units"],
        "counterfactual": None if not counterfactual else {
            "changed": counterfactual["changed"],
            "baseline_risk": counterfactual["baseline_risk"][i],
            "counterfactual_risk": counterfactual["counterfactual_risk"][i],
            "difference": counterfactual["difference"][i],
            "caveat": COUNTERFACTUAL_CAVEAT},
        "test_cohort_performance": {k: perf.get(k) for k in ["auroc", "auroc_ci", "brier", "ece", "calibration_slope"]},
        "explanation": narrative,
        "known_limitations": KNOWN_LIMITATIONS,
    }


def render_html(rep: dict) -> str:
    e = html.escape
    feats = "".join(f"<tr><td>{e(f['label'])}</td><td>{f['contribution']:+.4f}</td></tr>"
                    for f in rep["important_features"])
    cf = rep["counterfactual"]
    cf_html = "<p>No counterfactual scenario was run.</p>" if not cf else (
        "<p>" + e(", ".join(f"{c['label']}: {c['from']} → {c['to']}" for c in cf["changed"])) + "</p>"
        f"<p>Risk {cf['baseline_risk']:.3f} → {cf['counterfactual_risk']:.3f} "
        f"(difference {cf['difference']:+.3f})</p><p class='caveat'>{e(cf['caveat'])}</p>")
    perf = rep["test_cohort_performance"]
    ci = perf.get("auroc_ci") or [float("nan"), float("nan")]
    tech = "".join(f"<li>{e(t)}</li>" for t in rep["explanation"]["technical"])
    plain = "".join(f"<h4>{e(k.title())}</h4><p>{e(v)}</p>" for k, v in rep["explanation"]["plain_language"].items() if v)
    lims = "".join(f"<li>{e(x)}</li>" for x in rep["known_limitations"])
    p = rep["prediction"]
    u = rep["uncertainty"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(rep['title'])}</title>
<style>body{{font-family:Georgia,serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#1b1b1b;line-height:1.5}}
.banner{{background:#fff4d6;border:2px solid #b7791f;padding:.75rem 1rem;font-weight:bold}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:.35rem;text-align:left}}
h1{{font-size:1.6rem}}h2{{font-size:1.15rem;margin-top:1.6rem;border-bottom:1px solid #888}}.caveat{{font-style:italic}}
code{{font-family:ui-monospace,monospace}}</style></head><body>
<div class="banner">{e(rep['disclaimer'])}</div>
<h1>{e(rep['title'])}</h1>
<table><tr><th>Sample identifier</th><td><code>{e(rep['patient_id'])}</code></td></tr>
<tr><th>Dataset type</th><td>{e(rep['dataset_type'])}</td></tr>
<tr><th>Model</th><td>{e(rep['model'])}</td></tr><tr><th>Model version</th><td>{e(rep['model_version'])}</td></tr>
<tr><th>Timestamp (UTC)</th><td>{e(rep['timestamp_utc'])}</td></tr></table>
<h2>Prediction</h2><p>{p['horizon_years']}-year estimated cumulative risk: <b>{p['risk']:.3f}</b>.
Trajectory (years 1–5): {', '.join(f'{x:.3f}' for x in p['trajectory'])}.</p>
<h2>Uncertainty</h2><p>{u['lower']:.3f} – {u['upper']:.3f} ({e(u['method'])}).</p>
<h2>Important features</h2><p>{e(rep['attribution_method'])} — units: {e(rep['attribution_units'])}.</p>
<table><tr><th>Feature</th><th>Contribution</th></tr>{feats}</table>
<h2>Counterfactual result</h2>{cf_html}
<h2>Synthetic test-cohort performance</h2><p>AUROC {perf.get('auroc', float('nan')):.3f} (95% CI {ci[0]:.3f}–{ci[1]:.3f}),
Brier {perf.get('brier', float('nan')):.3f}, ECE {perf.get('ece', float('nan')):.3f},
calibration slope {perf.get('calibration_slope', float('nan')):.2f}.</p>
<h2>Technical explanation</h2><ul>{tech}</ul>
<h2>Plain-language explanation</h2>{plain}
<h2>Known limitations</h2><ul>{lims}</ul>
<p><small>Generated by PATIENT-XAI, a pre-application research demonstrator. Not for clinical use.</small></p>
</body></html>"""


def render_pdf(rep: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    e = html.escape
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=rep["title"])
    story = []
    banner = Table([[Paragraph(f"<b>{e(rep['disclaimer'])}</b>", ss["BodyText"])]], colWidths=[174 * mm])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff4d6")),
                                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#b7791f"))]))
    story += [banner, Spacer(1, 6), Paragraph(e(rep["title"]), ss["Title"])]
    meta = [["Sample identifier", rep["patient_id"]], ["Dataset type", rep["dataset_type"]],
            ["Model", rep["model"]], ["Model version", rep["model_version"]], ["Timestamp (UTC)", rep["timestamp_utc"]]]
    t = Table([[Paragraph(f"<b>{e(a)}</b>", ss["BodyText"]), Paragraph(e(str(b)), ss["BodyText"])] for a, b in meta],
              colWidths=[45 * mm, 129 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.grey)]))
    story += [t]
    p, u = rep["prediction"], rep["uncertainty"]

    def sec(title, text):
        story.extend([Paragraph(e(title), ss["Heading2"]), Paragraph(text, ss["BodyText"])])

    sec("Prediction", f"{p['horizon_years']}-year estimated cumulative risk: <b>{p['risk']:.3f}</b>. Trajectory: "
        + ", ".join(f"{x:.3f}" for x in p["trajectory"]))
    sec("Uncertainty", f"{u['lower']:.3f} – {u['upper']:.3f} ({e(u['method'])})")
    sec("Important features", e(rep["attribution_method"]) + " — " + e(rep["attribution_units"]) + "<br/>"
        + "<br/>".join(f"{e(f['label'])}: {f['contribution']:+.4f}" for f in rep["important_features"]))
    cf = rep["counterfactual"]
    sec("Counterfactual result", "No counterfactual scenario was run." if not cf else (
        e(", ".join(f"{c['label']}: {c['from']} → {c['to']}" for c in cf["changed"]))
        + f"<br/>Risk {cf['baseline_risk']:.3f} → {cf['counterfactual_risk']:.3f} (difference {cf['difference']:+.3f})"
        + f"<br/><i>{e(cf['caveat'])}</i>"))
    sec("Technical explanation", "<br/>".join("• " + e(x) for x in rep["explanation"]["technical"]))
    sec("Plain-language explanation", "<br/><br/>".join(
        f"<b>{e(k.title())}.</b> {e(v)}" for k, v in rep["explanation"]["plain_language"].items() if v))
    sec("Known limitations", "<br/>".join("• " + e(x) for x in rep["known_limitations"]))
    doc.build(story)
    return buf.getvalue()
