"""Application service: wires the repository, the trained model bundle and the
Explanation Engine together. Holds no clinical logic of its own."""

from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from patientxai import COUNTERFACTUAL_CAVEAT, DISCLAIMER, MODEL_VERSION
from patientxai.bundle import ModelBundle
from patientxai.config import HORIZONS, LABELS, MODIFIABLE, PRIMARY_HORIZON, UNITS, PipelineConfig
from patientxai.explanation_engine import generate
from patientxai.report import build_report, render_html, render_pdf
from patientxai.simulate import true_risk_curve

from .db import Repository

ROOT = Path(__file__).resolve().parents[2]


def _clean(o):
    """Make pandas/numpy values JSON-safe (NaN -> None)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    return o


class NotFound(Exception):
    pass


class Service:
    def __init__(self, artifacts_dir: Path | None = None, data_dir: Path | None = None,
                 database_url: str | None = None):
        cfg = PipelineConfig()
        self.artifacts_dir = Path(artifacts_dir or os.environ.get("PATIENTXAI_ARTIFACTS", cfg.artifacts_dir))
        self.data_dir = Path(data_dir or os.environ.get("PATIENTXAI_DATA", cfg.data_dir))
        self.repo = Repository(database_url)
        if not self.repo.is_seeded():
            self.repo.seed_from_csv(self.data_dir)
        self.bundle = ModelBundle.load(self.artifacts_dir)
        self.performance = json.loads((self.artifacts_dir / "performance.json").read_text())
        self.audit = json.loads((self.artifacts_dir / "counterfactual_audit.json").read_text())
        self.manifest = self.bundle.meta
        self.patients = self.repo.frame("patients")
        visits = self.repo.frame("visits").sort_values(["patient_id", "visit_index"])
        self._visits = {pid: g.reset_index(drop=True) for pid, g in visits.groupby("patient_id")}
        self.outcomes = self.repo.frame("outcomes").set_index("patient_id")
        self.truth = self.repo.frame("simulator_truth").set_index("patient_id")
        tr = self.patients[self.patients.split == "train"]
        X, L, _, ids = self.bundle.fs.sequences(visits[visits.patient_id.isin(tr.patient_id)], tr)
        self.bundle.set_reference(ids, X, L, self.repo.frame("outcomes"))
        self._explain_cached = lru_cache(maxsize=512)(self._explain_uncached)

    # ------------------------------------------------------------------ helpers
    def _patient(self, pid: str) -> dict:
        row = self.patients[self.patients.patient_id == pid]
        if row.empty:
            raise NotFound(pid)
        return row.iloc[0].to_dict()

    def _visits_of(self, pid: str) -> pd.DataFrame:
        if pid not in self._visits:
            raise NotFound(pid)
        return self._visits[pid]

    # ---------------------------------------------------------------- metadata
    def meta(self) -> dict:
        counts = self.patients.split.value_counts().to_dict()
        return {
            "name": "PATIENT-XAI", "model_version": MODEL_VERSION, "disclaimer": DISCLAIMER,
            "counterfactual_caveat": COUNTERFACTUAL_CAVEAT,
            "dataset_type": self.manifest["dataset_type"], "created_utc": self.manifest["created_utc"],
            "horizons_years": HORIZONS, "primary_horizon": PRIMARY_HORIZON,
            "models": {"gru": self.bundle.gru.name, "baseline": self.bundle.baseline.name},
            "modifiable": {k: {**v, "label": LABELS[k], "unit": UNITS.get(k, "")} for k, v in MODIFIABLE.items()},
            "cohort_counts": {k: int(v) for k, v in counts.items()},
            "n_gru_members": len(self.bundle.gru.members),
            "data_sha256_16": self.manifest["data_sha256_16"],
        }

    # ---------------------------------------------------------------- patients
    def list_patients(self, split=None, q=None, limit=50, offset=0) -> dict:
        df = self.patients
        if split:
            df = df[df.split == split]
        if q:
            df = df[df.patient_id.str.contains(q.upper(), regex=False)]
        page = df.iloc[offset: offset + limit]
        cols = ["patient_id", "sex", "age_at_index", "n_visits", "smoking_status", "split", "enrol_year"]
        return {"total": int(len(df)), "items": _clean(page[cols].to_dict("records"))}

    def patient_detail(self, pid: str) -> dict:
        p = self._patient(pid)
        v = self._visits_of(pid)
        out = self.outcomes.loc[pid].to_dict()
        latest = {}
        for c in ["sbp", "dbp", "heart_rate", "bmi", "hba1c", "ldl", "hdl", "activity", "antihypertensive", "statin"]:
            s = v[c].dropna()
            latest[c] = {"value": None if s.empty else float(s.iloc[-1]), "label": LABELS[c], "unit": UNITS.get(c, ""),
                         "date": None if s.empty else v.loc[s.index[-1], "visit_date"]}
        cols = ["visit_index", "visit_date", "t_years", "age", "bmi", "sbp", "dbp", "heart_rate", "hba1c", "ldl",
                "hdl", "activity", "antihypertensive", "statin", "imaging_observed"]
        return _clean({
            "patient": p, "visits": v[cols].to_dict("records"), "latest": latest,
            "observed_outcome": {"event": int(out["event"]), "follow_up_years": float(out["time"]),
                                 "note": "Synthetic outcome after the index visit; never shown to the model as input."},
            "disclaimer": DISCLAIMER,
        })

    # -------------------------------------------------------------- prediction
    def _context(self, pid):
        v = self._visits_of(pid)
        return len(v), float(v.t_years.iloc[-1])

    def predict(self, pid: str, model: str) -> dict:
        p, v = self._patient(pid), self._visits_of(pid)
        pred = self.bundle.predict(p, v, model)
        expl = self._explain_cached(pid, model, PRIMARY_HORIZON)
        n, span = self._context(pid)
        narrative = generate(pred, expl, None, self.performance, n, span)
        self.repo.log(pid, model, MODEL_VERSION, "predict", {"risk": pred["risk"]})
        return _clean({"patient_id": pid, "prediction": pred, "explanation": narrative,
                       "disclaimer": DISCLAIMER})

    def _explain_uncached(self, pid, model, horizon):
        return self.bundle.explain(self._patient(pid), self._visits_of(pid), model, horizon)

    def explain(self, pid: str, model: str, horizon: int) -> dict:
        p, v = self._patient(pid), self._visits_of(pid)
        expl = self._explain_cached(pid, model, horizon)
        pred = self.bundle.predict(p, v, model)
        n, span = self._context(pid)
        return _clean({"patient_id": pid, "attribution": expl,
                       "explanation": generate(pred, expl, None, self.performance, n, span),
                       "disclaimer": DISCLAIMER})

    # ---------------------------------------------------------- counterfactual
    def counterfactual(self, pid: str, model: str, changes: dict) -> dict:
        p, v = self._patient(pid), self._visits_of(pid)
        cf = self.bundle.counterfactual(p, v, changes, model)
        pred = self.bundle.predict(p, v, model)
        expl = self._explain_cached(pid, model, PRIMARY_HORIZON)
        n, span = self._context(pid)
        narrative = generate(pred, expl, cf, self.performance, n, span)
        truth = self.truth.loc[pid].to_dict()
        t_change = dict(changes)
        if "ldl" in t_change:
            last_ldl = v["ldl"].dropna()
            ref = float(last_ldl.iloc[-1]) if not last_ldl.empty else truth["ldl_index"]
            t_change["ldl"] = truth["ldl_index"] + (float(changes["ldl"]) - ref)
        t0, t1 = true_risk_curve(truth), true_risk_curve(truth, t_change)
        self.repo.log(pid, model, MODEL_VERSION, "counterfactual", {"changes": changes, "diff": cf["difference"]})
        return _clean({
            "patient_id": pid, "counterfactual": cf, "explanation": narrative,
            "caveat": COUNTERFACTUAL_CAVEAT,
            "simulator_ground_truth": {
                "baseline_risk": t0.tolist(), "counterfactual_risk": t1.tolist(), "difference": (t1 - t0).tolist(),
                "note": ("Available ONLY because the data are synthetic and the data-generating process is known. "
                         "Shown to expose where model-based simulation and true interventional effects diverge. "
                         "In real data this quantity is unobservable."),
            },
            "disclaimer": DISCLAIMER,
        })

    def similar(self, pid: str, k: int) -> dict:
        p, v = self._patient(pid), self._visits_of(pid)
        res = self.bundle.similar(p, v, k)
        pred = self.bundle.predict(p, v, "gru")
        res["this_patient_predicted_risk"] = pred["risk"][HORIZONS.index(PRIMARY_HORIZON)]
        return _clean(res)

    def performance_report(self) -> dict:
        return _clean({"performance": self.performance, "counterfactual_audit": self.audit,
                       "disclaimer": DISCLAIMER})

    # ------------------------------------------------------------------ report
    def report(self, pid: str, model: str, changes: dict | None, fmt: str):
        p, v = self._patient(pid), self._visits_of(pid)
        pred = self.bundle.predict(p, v, model)
        expl = self._explain_cached(pid, model, PRIMARY_HORIZON)
        cf = self.bundle.counterfactual(p, v, changes, model) if changes else None
        n, span = self._context(pid)
        narrative = generate(pred, expl, cf, self.performance, n, span)
        rep = build_report(pid, pred, expl, narrative, cf, self.performance, self.manifest["dataset_type"])
        self.repo.log(pid, model, MODEL_VERSION, "report", {"format": fmt})
        rep = _clean(rep)
        if fmt == "html":
            return render_html(rep)
        if fmt == "pdf":
            return render_pdf(rep)
        return rep
