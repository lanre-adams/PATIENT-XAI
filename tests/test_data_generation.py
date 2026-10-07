"""Unit tests for the synthetic cohort simulator and splits."""

import numpy as np
import pandas as pd

from patientxai.config import HORIZONS, IMAGING
from patientxai.simulate import assign_split, horizon_label, simulate_cohort, true_risk_curve


def test_simulator_is_deterministic():
    a, b = simulate_cohort(40, seed=3), simulate_cohort(40, seed=3)
    pd.testing.assert_frame_equal(a.visits, b.visits)
    pd.testing.assert_frame_equal(a.outcomes, b.outcomes)


def test_cohort_is_longitudinal_and_synthetic():
    c = simulate_cohort(80, seed=1)
    per = c.visits.groupby("patient_id").size()
    assert per.min() >= 3, "every synthetic patient must have repeated observations"
    assert c.patients.patient_id.str.match(r"^SYN-\d{5}$").all()
    # irregular sampling: visit gaps are not constant
    gaps = c.visits.groupby("patient_id").t_years.diff().dropna()
    assert gaps.std() > 0.05
    # informative intermittent missingness is present and masked consistently
    assert c.visits.hba1c.isna().any()
    assert (c.visits.hba1c.isna() == (c.visits.hba1c_observed == 0)).all()
    assert (c.visits[IMAGING[0]].isna() == (c.visits.imaging_observed == 0)).all()


def test_outcomes_and_labels_are_consistent():
    c = simulate_cohort(300, seed=2)
    o = c.outcomes
    assert ((o.time > 0) & (o.time <= 5.0001)).all()
    lab3 = horizon_label(o, 3)
    assert set(lab3.dropna().unique()) <= {0.0, 1.0}
    censored_early = (o.event == 0) & (o.time < 3)
    assert lab3[censored_early].isna().all(), "status at 3y is unknown for early-censored patients"
    assert 0.05 < lab3.mean() < 0.5


def test_true_risk_curve_monotone_and_causal_structure():
    c = simulate_cohort(30, seed=4)
    t = c.truth.iloc[0].to_dict()
    base = true_risk_curve(t)
    assert len(base) == len(HORIZONS) and np.all(np.diff(base) >= 0)
    assert true_risk_curve(t, {"sbp": t["sbp_index"] - 20})[-1] < base[-1]
    # BMI and HbA1c are markers, not causes, in this simulator
    assert np.allclose(true_risk_curve(t, {"bmi": 20, "hba1c": 5.0}), base)
    t_ah = {**t, "antihypertensive_index": 0}
    assert true_risk_curve(t_ah, {"antihypertensive": 1})[-1] < true_risk_curve(t_ah)[-1]


def test_temporal_split():
    c = simulate_cohort(200, seed=5)
    s = assign_split(c.patients, 2019, 2020)
    assert set(np.unique(s)) <= {"train", "val", "test"}
    assert (c.patients.enrol_year[s == "test"] > 2020).all()
    assert (c.patients.enrol_year[s == "train"] <= 2019).all()
