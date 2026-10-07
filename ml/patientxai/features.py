"""Feature construction for the sequence model and the transparent baseline.

Design choices (each is a research question in its own right, see docs/research_problems.md):
* intermittently measured values are carried forward (LOCF) and paired with an
  explicit "was it measured at this visit" mask, so the sequence model can learn
  from informative missingness;
* irregular visit timing is encoded as the elapsed time since the previous visit;
* standardisation statistics are fitted on the TRAINING cohort only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import IMAGING, MASKS, STATIC, VISIT_BINARY, VISIT_NUMERIC

SEQ_FEATURES = VISIT_NUMERIC + VISIT_BINARY + MASKS + IMAGING + ["dt", "t_since_first"]
TAB_FEATURES = (VISIT_NUMERIC + VISIT_BINARY + STATIC + IMAGING
                + ["sbp_slope", "hba1c_slope", "bmi_slope", "n_visits", "imaging_ever"])
CONTINUOUS = VISIT_NUMERIC + IMAGING + ["dt", "t_since_first"]


def _slope(t: np.ndarray, y: np.ndarray) -> float:
    ok = ~np.isnan(y)
    if ok.sum() < 2 or np.ptp(t[ok]) < 1e-6:
        return 0.0
    return float(np.polyfit(t[ok], y[ok], 1)[0])


@dataclass
class FeatureSpace:
    mean: dict = field(default_factory=dict)
    std: dict = field(default_factory=dict)
    tab_mean: dict = field(default_factory=dict)
    tab_std: dict = field(default_factory=dict)
    max_len: int = 13

    # ------------------------------------------------------------------ fitting
    def fit(self, visits: pd.DataFrame, patients: pd.DataFrame) -> FeatureSpace:
        v = self._prepare(visits)
        for c in CONTINUOUS:
            self.mean[c] = float(np.nanmean(v[c]))
            self.std[c] = float(np.nanstd(v[c]) or 1.0)
        self.max_len = int(visits.groupby("patient_id").size().max())
        tab = self._tabular_raw(visits, patients)
        for c in TAB_FEATURES:
            self.tab_mean[c] = float(np.nanmean(tab[c]))
            self.tab_std[c] = float(np.nanstd(tab[c]) or 1.0)
        return self

    # --------------------------------------------------------------- transforms
    @staticmethod
    def _prepare(visits: pd.DataFrame) -> pd.DataFrame:
        v = visits.sort_values(["patient_id", "visit_index"]).copy()
        locf = ["hba1c", "ldl", "hdl"] + IMAGING
        v[locf] = v.groupby("patient_id")[locf].ffill()
        v["dt"] = v.groupby("patient_id")["t_years"].diff().fillna(0.0)
        v["t_since_first"] = v["t_years"]
        return v

    def sequences(self, visits: pd.DataFrame, patients: pd.DataFrame):
        """Return (X[N,T,F], lengths[N], static[N,S], ids) with left-aligned padding."""
        v = self._prepare(visits)
        for c in CONTINUOUS:
            v[c] = ((v[c] - self.mean[c]) / self.std[c]).fillna(0.0)
        ids = list(patients.patient_id)
        groups = dict(tuple(v.groupby("patient_id")))
        T = max(self.max_len, max(len(g) for g in groups.values()))
        X = np.zeros((len(ids), T, len(SEQ_FEATURES)), dtype=np.float32)
        lengths = np.zeros(len(ids), dtype=np.int64)
        for n, pid in enumerate(ids):
            g = groups[pid][SEQ_FEATURES].to_numpy(dtype=np.float32)
            X[n, : len(g)] = g
            lengths[n] = len(g)
        S = patients[STATIC].to_numpy(dtype=np.float32)
        return X, lengths, S, ids

    def _tabular_raw(self, visits: pd.DataFrame, patients: pd.DataFrame) -> pd.DataFrame:
        v = self._prepare(visits)
        raw_hba1c = visits.sort_values(["patient_id", "visit_index"]).groupby("patient_id")["hba1c"]
        raw_hba1c = {pid: s.to_numpy(float) for pid, s in raw_hba1c}
        rows = []
        for pid, g in v.groupby("patient_id", sort=False):
            last = g.iloc[-1]
            r = {c: last[c] for c in VISIT_NUMERIC + VISIT_BINARY + IMAGING}
            t = g["t_years"].to_numpy(float)
            r["sbp_slope"] = _slope(t, g["sbp"].to_numpy(float))
            r["hba1c_slope"] = _slope(t, raw_hba1c[pid])  # slope on measured values only
            r["bmi_slope"] = _slope(t, g["bmi"].to_numpy(float))
            r["n_visits"] = len(g)
            r["imaging_ever"] = float(g["imaging_observed"].max())
            r["patient_id"] = pid
            rows.append(r)
        tab = pd.DataFrame(rows).set_index("patient_id")
        p = patients.set_index("patient_id")
        for c in STATIC:
            tab[c] = p.loc[tab.index, c].astype(float)
        return tab.loc[list(patients.patient_id)].reset_index()

    def tabular(self, visits: pd.DataFrame, patients: pd.DataFrame) -> np.ndarray:
        tab = self._tabular_raw(visits, patients)
        out = np.zeros((len(tab), len(TAB_FEATURES)), dtype=np.float64)
        for j, c in enumerate(TAB_FEATURES):
            col = tab[c].astype(float).fillna(self.tab_mean[c])
            out[:, j] = (col - self.tab_mean[c]) / self.tab_std[c]
        return out

    # ------------------------------------------------------------- persistence
    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: Path) -> FeatureSpace:
        return cls(**json.loads(Path(path).read_text()))
