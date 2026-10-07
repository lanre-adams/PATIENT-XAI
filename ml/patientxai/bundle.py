"""Inference-time bundle: prediction, uncertainty, attribution, counterfactual
simulation and latent-space similarity for a single synthetic patient."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from .config import HORIZONS, IMAGING, LABELS, PRIMARY_HORIZON, STATIC
from .features import SEQ_FEATURES, TAB_FEATURES, FeatureSpace
from .models.gru import GRUEnsemble, TrajectoryGRU

MODEL_KEYS = ("gru", "baseline")


def _group(name: str) -> str:
    return "imaging_embedding" if name in IMAGING else name


def _label(name: str) -> str:
    if name == "imaging_embedding":
        return "Imaging-derived embedding (synthetic, 8 dims)"
    return LABELS.get(name, name)


class ModelBundle:
    def __init__(self, fs: FeatureSpace, baseline, gru: GRUEnsemble, meta: dict):
        self.fs, self.baseline, self.gru, self.meta = fs, baseline, gru, meta
        self._ref = None

    # ----------------------------------------------------------------- loading
    @classmethod
    def load(cls, artifacts_dir: Path) -> ModelBundle:
        d = Path(artifacts_dir)
        fs = FeatureSpace.load(d / "feature_space.json")
        base = joblib.load(d / "baseline.joblib")
        ck = torch.load(d / "gru_ensemble.pt", weights_only=False)
        members = []
        for sd in ck["state_dicts"]:
            m = TrajectoryGRU(ck["n_features"], ck["n_static"], ck["hidden"])
            m.load_state_dict(sd)
            m.eval()
            members.append(m)
        meta = json.loads((d / "manifest.json").read_text())
        return cls(fs, base, GRUEnsemble(members), meta)

    # ---------------------------------------------------------------- encoding
    def _encode(self, patient: dict, visits: pd.DataFrame):
        p = pd.DataFrame([{k: patient[k] for k in ["patient_id", *STATIC]}])
        v = visits.copy()
        v["patient_id"] = patient["patient_id"]
        X, L, S, _ = self.fs.sequences(v, p)
        T = self.fs.tabular(v, p)
        return X, L, S, T

    def members(self, patient: dict, visits: pd.DataFrame, model: str) -> np.ndarray:
        X, L, S, T = self._encode(patient, visits)
        if model == "gru":
            return self.gru.predict_members(X, L, S)[:, 0, :]
        if model == "baseline":
            return self.baseline.predict_members(T)[:, 0, :]
        raise ValueError(f"unknown model {model!r}; expected one of {MODEL_KEYS}")

    def point(self, patient, visits, model) -> np.ndarray:
        if model == "baseline":
            _, _, _, T = self._encode(patient, visits)
            return self.baseline.predict_risk(T)[0]
        return self.members(patient, visits, model).mean(0)

    # -------------------------------------------------------------- prediction
    def predict(self, patient: dict, visits: pd.DataFrame, model: str = "gru") -> dict:
        mem = self.members(patient, visits, model)
        pt = self.point(patient, visits, model)
        return {
            "model": model,
            "model_name": self.gru.name if model == "gru" else self.baseline.name,
            "horizons_years": HORIZONS,
            "risk": pt.tolist(),
            "lower": np.percentile(mem, 5, axis=0).tolist(),
            "upper": np.percentile(mem, 95, axis=0).tolist(),
            "member_std": mem.std(0).tolist(),
            "n_members": int(len(mem)),
            "uncertainty_method": ("Deep-ensemble spread (5th-95th percentile of members)" if model == "gru"
                                   else "Bootstrap refits (5th-95th percentile)"),
            "primary_horizon": PRIMARY_HORIZON,
        }

    # ----------------------------------------------------------- attribution
    def explain(self, patient: dict, visits: pd.DataFrame, model: str = "gru",
                horizon: int = PRIMARY_HORIZON, steps: int = 32) -> dict:
        X, L, S, T = self._encode(patient, visits)
        last = visits.sort_values("visit_index").iloc[-1]
        h_i = HORIZONS.index(horizon)
        contrib: dict[str, float] = {}
        temporal = None
        if model == "gru":
            ax, as_, fx, f0 = self.gru.integrated_gradients(X[0], int(L[0]), S[0], h_i, steps)
            for j, f in enumerate(SEQ_FEATURES):
                contrib[_group(f)] = contrib.get(_group(f), 0.0) + float(ax[:, j].sum())
            for j, f in enumerate(STATIC):
                contrib[f] = contrib.get(f, 0.0) + float(as_[j])
            per_visit_abs = np.abs(ax).sum(1)
            dates = visits.sort_values("visit_index")["visit_date"].tolist()
            temporal = [{"visit_index": i, "visit_date": dates[i], "signed": float(ax[i].sum()),
                         "share": float(per_visit_abs[i] / max(per_visit_abs.sum(), 1e-12))}
                        for i in range(int(L[0]))]
            total = sum(contrib.values())
            method = "Integrated gradients (all-zero standardised baseline), ensemble mean"
            units = f"change in {horizon}-year cumulative risk (probability)"
            completeness = {"sum_attributions": total, "f_x_minus_f_baseline": fx - f0,
                            "gap": abs(total - (fx - f0))}
        else:
            a = self.baseline.attributions(T[0])
            for j, f in enumerate(TAB_FEATURES):
                contrib[_group(f)] = contrib.get(_group(f), 0.0) + float(a[j])
            method = "Exact linear attribution w_j * x_j (standardised features, training-mean reference)"
            units = "contribution to annual hazard log-odds"
            completeness = None
        rows = []
        for k, v in contrib.items():
            value = None
            if k in last.index and k not in IMAGING:
                value = None if pd.isna(last[k]) else float(last[k])
            elif k in patient:
                value = float(patient[k])
            rows.append({"feature": k, "label": _label(k), "contribution": v,
                         "direction": "raises estimate" if v > 0 else "lowers estimate", "value": value})
        rows.sort(key=lambda r: -abs(r["contribution"]))
        return {"model": model, "horizon_years": horizon, "method": method, "units": units,
                "contributions": rows, "temporal": temporal, "completeness": completeness}

    # --------------------------------------------------------- counterfactual
    @staticmethod
    def apply_changes(patient: dict, visits: pd.DataFrame, changes: dict):
        p = dict(patient)
        v = visits.sort_values("visit_index").copy().reset_index(drop=True)
        i = len(v) - 1
        changed = []
        for k, val in changes.items():
            if k == "smoking_current":
                old = int(p.get("smoking_current", 0))
                p["smoking_current"] = int(val)
                if old == 1 and int(val) == 0:
                    p["smoking_former"] = 1
                changed.append({"variable": k, "label": LABELS[k], "from": old, "to": int(val)})
                continue
            if k not in v.columns:
                raise ValueError(f"variable {k!r} cannot be modified")
            old = v.at[i, k]
            v.at[i, k] = float(val)
            if k == "hba1c":
                v.at[i, "hba1c_observed"] = 1
            if k == "ldl":
                v.at[i, "lipids_observed"] = 1
            changed.append({"variable": k, "label": LABELS.get(k, k),
                            "from": None if pd.isna(old) else float(old), "to": float(val)})
        return p, v, changed

    def counterfactual(self, patient: dict, visits: pd.DataFrame, changes: dict, model: str = "gru") -> dict:
        p2, v2, changed = self.apply_changes(patient, visits, changes)
        m0 = self.members(patient, visits, model)
        m1 = self.members(p2, v2, model)
        r0, r1 = self.point(patient, visits, model), self.point(p2, v2, model)
        d = m1 - m0  # paired across members
        return {
            "model": model, "horizons_years": HORIZONS, "changed": changed,
            "baseline_risk": r0.tolist(), "counterfactual_risk": r1.tolist(),
            "difference": (r1 - r0).tolist(),
            "relative_difference": ((r1 - r0) / np.clip(r0, 1e-9, None)).tolist(),
            "difference_lower": np.percentile(d, 5, axis=0).tolist(),
            "difference_upper": np.percentile(d, 95, axis=0).tolist(),
            "scope": "Change applied to the most recent (index) visit only; earlier history unchanged.",
        }

    # ------------------------------------------------------------- similarity
    def set_reference(self, ids, X, L, outcomes: pd.DataFrame):
        Z = self.gru.embed(X, L)
        Z = Z / np.linalg.norm(Z, axis=1, keepdims=True).clip(1e-9)
        self._ref = (list(ids), Z, outcomes.set_index("patient_id"))

    def similar(self, patient: dict, visits: pd.DataFrame, k: int = 10) -> dict:
        if self._ref is None:
            raise RuntimeError("reference cohort not set")
        ids, Z, out = self._ref
        X, L, _, _ = self._encode(patient, visits)
        z = self.gru.embed(X, L)[0]
        z = z / max(np.linalg.norm(z), 1e-9)
        sims = Z @ z
        order = [i for i in np.argsort(-sims) if ids[i] != patient["patient_id"]][:k]
        neigh = [{"patient_id": ids[i], "similarity": float(sims[i]),
                  "event": int(out.loc[ids[i], "event"]), "follow_up_years": float(out.loc[ids[i], "time"])}
                 for i in order]
        known3 = [n for n in neigh if n["event"] == 1 and n["follow_up_years"] <= PRIMARY_HORIZON
                  or n["follow_up_years"] >= PRIMARY_HORIZON]
        rate = (np.mean([1.0 if (n["event"] == 1 and n["follow_up_years"] <= PRIMARY_HORIZON) else 0.0
                         for n in known3]) if known3 else None)
        return {"k": k, "space": "GRU latent state z_t at index visit (cosine similarity, training cohort)",
                "neighbours": neigh, "observed_event_rate_by_primary_horizon": rate,
                "n_with_known_status": len(known3)}
