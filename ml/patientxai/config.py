"""Shared configuration: feature definitions, horizons and pipeline settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

HORIZONS = [1, 2, 3, 4, 5]  # years after the index (last observed) visit
PRIMARY_HORIZON = 3

# Time-varying clinical measurements recorded at visits (synthetic units).
VISIT_NUMERIC = [
    "age", "bmi", "sbp", "dbp", "heart_rate", "hba1c", "ldl", "hdl", "activity",
]
VISIT_BINARY = ["antihypertensive", "statin"]
# Measurements that are not taken at every visit -> missingness masks.
INTERMITTENT = {"hba1c": "hba1c_observed", "ldl": "lipids_observed", "hdl": "lipids_observed"}
MASKS = ["hba1c_observed", "lipids_observed", "imaging_observed"]
IMAGING_DIM = 8
IMAGING = [f"img_{i}" for i in range(IMAGING_DIM)]
STATIC = ["sex_male", "smoking_current", "smoking_former"]

UNITS = {
    "age": "years", "bmi": "kg/m²", "sbp": "mmHg", "dbp": "mmHg", "heart_rate": "bpm",
    "hba1c": "%", "ldl": "mmol/L", "hdl": "mmol/L", "activity": "min/week",
}

LABELS = {
    "age": "Age", "bmi": "BMI", "sbp": "Systolic BP", "dbp": "Diastolic BP",
    "heart_rate": "Heart rate", "hba1c": "HbA1c", "ldl": "LDL cholesterol",
    "hdl": "HDL cholesterol", "activity": "Physical activity",
    "antihypertensive": "Antihypertensive (synthetic)", "statin": "Statin (synthetic)",
    "hba1c_observed": "HbA1c measured", "lipids_observed": "Lipids measured",
    "imaging_observed": "Imaging available", "sex_male": "Sex (male)",
    "smoking_current": "Current smoker", "smoking_former": "Former smoker",
    "dt": "Time since previous visit", "t_since_first": "Time in observation",
    "n_visits": "Number of visits", "sbp_slope": "SBP trend", "hba1c_slope": "HbA1c trend",
    "bmi_slope": "BMI trend", "imaging_ever": "Any imaging available",
}
for _i in range(IMAGING_DIM):
    LABELS[f"img_{_i}"] = f"Imaging embedding dim {_i}"

# Variables a user may alter in the Counterfactual Explorer.
MODIFIABLE = {
    "sbp": {"min": 95, "max": 200, "step": 1},
    "ldl": {"min": 1.0, "max": 7.0, "step": 0.1},
    "bmi": {"min": 17, "max": 45, "step": 0.5},
    "hba1c": {"min": 4.5, "max": 11.0, "step": 0.1},
    "activity": {"min": 0, "max": 600, "step": 10},
    "smoking_current": {"min": 0, "max": 1, "step": 1},
}


@dataclass
class PipelineConfig:
    n_patients: int = 3000
    seed: int = 20261007
    n_gru_members: int = 7
    n_baseline_bootstrap: int = 30
    gru_hidden: int = 32
    gru_epochs: int = 60
    gru_patience: int = 8
    gru_lr: float = 3e-3
    ig_steps: int = 32
    n_bootstrap_metrics: int = 200
    train_until_year: int = 2019  # temporal split: enrolment year <= this -> train
    val_year: int = 2020          # == this -> validation; later -> test
    artifacts_dir: Path = field(default_factory=lambda: Path(os.environ.get(
        "PATIENTXAI_ARTIFACTS", Path(__file__).resolve().parents[2] / "artifacts")))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get(
        "PATIENTXAI_DATA", Path(__file__).resolve().parents[2] / "data" / "generated")))

    @classmethod
    def fast(cls, **kw) -> PipelineConfig:
        """Small configuration used by the automated tests."""
        base = dict(n_patients=500, n_gru_members=2, n_baseline_bootstrap=5,
                    gru_epochs=6, gru_patience=3, ig_steps=8, n_bootstrap_metrics=20)
        base.update(kw)
        return cls(**base)
