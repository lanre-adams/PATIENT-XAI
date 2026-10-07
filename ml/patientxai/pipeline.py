"""End-to-end pipeline: simulate -> split -> features -> train -> evaluate -> audit -> save.

Run with:  python -m scripts.run_pipeline   (or `make pipeline`)
Every number reported by the demonstrator is produced here from the synthetic data.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import torch

from . import MODEL_VERSION, __version__
from .config import HORIZONS, IMAGING, PRIMARY_HORIZON, PipelineConfig
from .evaluate import evaluate_binary, youden_threshold
from .features import SEQ_FEATURES, TAB_FEATURES, FeatureSpace
from .models.baseline import DiscreteTimeLogistic
from .models.gru import GRUEnsemble, survival_targets, train_member
from .simulate import assign_split, horizon_label, simulate_cohort, true_risk_curve

AUDIT_INTERVENTIONS = {
    "Lower SBP by 20 mmHg": lambda r: {"sbp": r["sbp"] - 20},
    "Lower LDL by 1.0 mmol/L": lambda r: {"ldl": r["ldl"] - 1.0},
    "Increase activity by 150 min/week": lambda r: {"activity": r["activity"] + 150},
    "Stop smoking (current smokers)": lambda r: {"smoking_current": 0},
    "Lower BMI by 3 kg/m²": lambda r: {"bmi": r["bmi"] - 3},
    "Lower HbA1c by 0.8%": lambda r: {"hba1c": r["hba1c"] - 0.8},
    "Set antihypertensive flag to 1 (no other change)": lambda r: {"antihypertensive": 1},
}


def imaging_ablation(X: np.ndarray) -> np.ndarray:
    Xa = X.copy()
    cols = [SEQ_FEATURES.index(c) for c in IMAGING + ["imaging_observed"]]
    Xa[:, :, cols] = 0.0
    return Xa


def _hash_frame(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]


def run_pipeline(cfg: PipelineConfig | None = None, log=print) -> dict:
    cfg = cfg or PipelineConfig()
    t0 = time.time()
    cfg.artifacts_dir.mkdir(parents=True, exist_ok=True)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)

    log(f"[1/6] Simulating {cfg.n_patients} synthetic patients (seed={cfg.seed})")
    c = simulate_cohort(cfg.n_patients, cfg.seed)
    c.patients["split"] = assign_split(c.patients, cfg.train_until_year, cfg.val_year)
    c.patients.to_csv(cfg.data_dir / "patients.csv", index=False)
    c.visits.to_csv(cfg.data_dir / "visits.csv", index=False)
    c.outcomes.to_csv(cfg.data_dir / "outcomes.csv", index=False)
    c.truth.to_csv(cfg.data_dir / "simulator_truth.csv", index=False)

    P, V, OUT = c.patients, c.visits, c.outcomes.set_index("patient_id").loc[c.patients.patient_id].reset_index()
    split = P["split"].to_numpy()
    tr, va, te = split == "train", split == "val", split == "test"

    log("[2/6] Building features (fitted on the training cohort only)")
    fs = FeatureSpace().fit(V[V.patient_id.isin(P.patient_id[tr])], P[tr])
    X, L, S, ids = fs.sequences(V, P)
    T = fs.tabular(V, P)
    ev, tm = OUT["event"].to_numpy(), OUT["time"].to_numpy()
    yk, mk = survival_targets(ev, tm)

    log(f"[3/6] Training baseline (+{cfg.n_baseline_bootstrap} bootstrap refits)")
    base = DiscreteTimeLogistic(n_bootstrap=cfg.n_baseline_bootstrap, seed=cfg.seed).fit(T[tr], ev[tr], tm[tr])

    def train_ensemble(Xs, n, tag):
        members, hist = [], []
        for m in range(n):
            model, h = train_member(
                (Xs[tr], L[tr], S[tr], yk[tr], mk[tr]), (Xs[va], L[va], S[va], yk[va], mk[va]),
                n_features=Xs.shape[2], n_static=S.shape[1], hidden=cfg.gru_hidden,
                epochs=cfg.gru_epochs, patience=cfg.gru_patience, lr=cfg.gru_lr, seed=cfg.seed + 101 * m)
            members.append(model)
            hist.append(h)
            log(f"      {tag} member {m + 1}/{n}: {len(h)} epochs, best val NLL {min(h):.4f}")
        return GRUEnsemble(members), hist

    log(f"[4/6] Training GRU ensemble ({cfg.n_gru_members} members) and no-imaging ablation")
    gru, hist = train_ensemble(X, cfg.n_gru_members, "GRU")
    Xa = imaging_ablation(X)
    gru_noimg, _ = train_ensemble(Xa, max(1, min(3, cfg.n_gru_members)), "GRU-no-imaging")

    log("[5/6] Evaluating on the temporally held-out test cohort")
    preds = {
        "baseline": base.predict_risk(T),
        "gru": gru.predict_risk(X, L, S),
        "gru_no_imaging": gru_noimg.predict_risk(Xa, L, S),
    }
    names = {"baseline": base.name, "gru": gru.name, "gru_no_imaging": "GRU ensemble without imaging (ablation)"}
    hp = HORIZONS.index(PRIMARY_HORIZON)
    lab_p = horizon_label(OUT, PRIMARY_HORIZON).to_numpy()
    perf = {"primary_horizon": PRIMARY_HORIZON, "models": {}, "cohort": {}}
    for split_name, msk in [("train", tr), ("val", va), ("test", te)]:
        perf["cohort"][split_name] = {
            "patients": int(msk.sum()),
            "enrolment_years": sorted(int(y) for y in P.enrol_year[msk].unique()),
            "events_observed": int(ev[msk].sum()),
            "known_status_at_primary_horizon": int((~np.isnan(lab_p) & msk).sum()),
        }
    for key, p in preds.items():
        known_va = va & ~np.isnan(lab_p)
        thr = youden_threshold(lab_p[known_va].astype(int), p[known_va, hp])
        by_h = {}
        for h_i, h in enumerate(HORIZONS):
            lab = horizon_label(OUT, h).to_numpy()
            k = te & ~np.isnan(lab)
            if lab[k].min() == lab[k].max():
                continue
            by_h[str(h)] = evaluate_binary(lab[k], p[k, h_i], thr if h == PRIMARY_HORIZON else 0.5,
                                           n_boot=cfg.n_bootstrap_metrics, seed=cfg.seed)
        sub = {}
        for sex in ["F", "M"]:
            k = te & ~np.isnan(lab_p) & (P.sex.to_numpy() == sex)
            r = evaluate_binary(lab_p[k], p[k, hp], thr, n_boot=max(20, cfg.n_bootstrap_metrics // 4), seed=cfg.seed)
            sub[sex] = {x: r[x] for x in ["n", "events", "prevalence", "mean_predicted", "auroc", "brier",
                                         "sensitivity", "specificity"]}
        perf["models"][key] = {"name": names[key], "threshold_source": "Youden index on validation cohort",
                               "by_horizon": by_h, "subgroups_sex": sub}

    log("[6/6] Counterfactual audit: model-based simulation vs simulator ground truth")
    from .bundle import ModelBundle  # local import to avoid cycle
    truth = c.truth.set_index("patient_id")
    rng = np.random.default_rng(cfg.seed)
    test_ids = list(np.array(ids)[te])
    sample = rng.choice(test_ids, size=min(150, len(test_ids)), replace=False)
    bundle = ModelBundle(fs=fs, baseline=base, gru=gru, meta={})
    audit = {}
    vg = dict(tuple(V.groupby("patient_id")))
    pr = P.set_index("patient_id")
    for label, make in AUDIT_INTERVENTIONS.items():
        rows = {"gru": [], "baseline": [], "truth": []}
        for pid in sample:
            prow = pr.loc[pid].to_dict()
            prow["patient_id"] = pid
            if label.startswith("Stop smoking") and not prow["smoking_current"]:
                continue
            visits = vg[pid]
            last = visits.sort_values("visit_index").iloc[-1].to_dict()
            if np.isnan(last.get("ldl", np.nan)):
                last["ldl"] = float(visits["ldl"].dropna().iloc[-1]) if visits["ldl"].notna().any() else 3.3
            if np.isnan(last.get("hba1c", np.nan)):
                last["hba1c"] = float(visits["hba1c"].dropna().iloc[-1]) if visits["hba1c"].notna().any() else 5.6
            last["smoking_current"] = prow["smoking_current"]
            change = make(last)
            for mdl in ["gru", "baseline"]:
                cf = bundle.counterfactual(prow, visits, change, model=mdl)
                rows[mdl].append(cf["difference"][hp])
            tr_row = truth.loc[pid].to_dict()
            t_change = dict(change)
            if "ldl" in t_change:  # express relative to the true (possibly unmeasured) value
                t_change["ldl"] = tr_row["ldl_index"] + (change["ldl"] - last["ldl"])
            rows["truth"].append(float(true_risk_curve(tr_row, t_change)[hp] - true_risk_curve(tr_row)[hp]))
        g, b, t = (np.array(rows[k]) for k in ["gru", "baseline", "truth"])
        audit[label] = {
            "n": int(len(t)),
            "true_mean_change": float(t.mean()),
            "gru_mean_change": float(g.mean()), "baseline_mean_change": float(b.mean()),
            "gru_corr_with_truth": float(np.corrcoef(g, t)[0, 1]) if t.std() > 1e-9 and g.std() > 1e-9 else None,
            "gru_sign_agreement": float(np.mean(np.sign(g) == np.sign(t))) if t.std() > 1e-9 else None,
            "causal_in_simulator": label.split()[1] not in {"BMI", "HbA1c"},
        }

    log("Saving artifacts")
    joblib.dump(base, cfg.artifacts_dir / "baseline.joblib")
    torch.save({"state_dicts": gru.state_dicts(), "n_features": X.shape[2], "n_static": S.shape[1],
                "hidden": cfg.gru_hidden}, cfg.artifacts_dir / "gru_ensemble.pt")
    fs.save(cfg.artifacts_dir / "feature_space.json")
    (cfg.artifacts_dir / "performance.json").write_text(json.dumps(perf, indent=2))
    (cfg.artifacts_dir / "counterfactual_audit.json").write_text(json.dumps(
        {"horizon_years": PRIMARY_HORIZON, "n_sampled_test_patients": int(len(sample)), "interventions": audit},
        indent=2))
    manifest = {
        "package_version": __version__, "model_version": MODEL_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {k: (str(v) if not isinstance(v, (int, float)) else v) for k, v in cfg.__dict__.items()},
        "data_sha256_16": {"visits": _hash_frame(V), "patients": _hash_frame(P)},
        "seq_features": SEQ_FEATURES, "tab_features": TAB_FEATURES,
        "training_history_val_nll": hist, "runtime_seconds": round(time.time() - t0, 1),
        "dataset_type": "SYNTHETIC (simulated cohort; no real patient data)",
    }
    (cfg.artifacts_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"Done in {manifest['runtime_seconds']} s")
    return {"performance": perf, "audit": audit, "manifest": manifest}
