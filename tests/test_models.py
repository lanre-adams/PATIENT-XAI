"""Model tests: inference shapes, monotone risk curves, uncertainty, attribution properties."""

import numpy as np
import pytest

from patientxai.bundle import ModelBundle
from patientxai.config import HORIZONS
from patientxai.features import FeatureSpace
from patientxai.models.baseline import person_period
from patientxai.models.gru import survival_targets

pytestmark = pytest.mark.model


@pytest.fixture(scope="module")
def bundle(pipeline_dirs):
    return ModelBundle.load(pipeline_dirs["cfg"].artifacts_dir)


@pytest.fixture(scope="module")
def one(service, test_patient_id):
    return service._patient(test_patient_id), service._visits_of(test_patient_id)


def test_survival_targets_respect_censoring():
    y, m = survival_targets(np.array([1, 0, 0]), np.array([2.3, 2.7, 5.0]))
    assert y[0].tolist() == [0, 0, 1, 0, 0] and m[0].tolist() == [1, 1, 1, 0, 0]
    assert y[1].sum() == 0 and m[1].tolist() == [1, 1, 0, 0, 0]
    assert m[2].sum() == 5


def test_person_period_expansion():
    X = np.zeros((2, 3))
    Xp, yp = person_period(X, np.array([1, 0]), np.array([1.5, 3.2]))
    assert len(Xp) == 2 + 3 and yp.tolist() == [0, 1, 0, 0, 0]


@pytest.mark.parametrize("model", ["gru", "baseline"])
def test_prediction_is_valid_monotone_risk_with_interval(bundle, one, model):
    p = bundle.predict(*one, model=model)
    r, lo, hi = map(np.array, (p["risk"], p["lower"], p["upper"]))
    assert len(r) == len(HORIZONS)
    assert np.all((r >= 0) & (r <= 1)) and np.all(np.diff(r) >= -1e-9)
    assert np.all(lo <= hi + 1e-12)


def test_integrated_gradients_completeness(bundle, one):
    e = bundle.explain(*one, model="gru", horizon=3, steps=64)
    c = e["completeness"]
    assert abs(c["gap"]) < 0.02 + 0.2 * abs(c["f_x_minus_f_baseline"])
    assert e["temporal"] and abs(sum(t["share"] for t in e["temporal"]) - 1) < 1e-6


def test_baseline_attribution_is_exact_on_logit_scale(bundle, one, service):
    p, v = one
    _, _, _, T = bundle._encode(p, v)
    a = bundle.baseline.attributions(T[0])
    m = bundle.baseline.model
    logit_year1 = float(m.decision_function(np.hstack([T[0], np.eye(5)[0]])[None])[0])
    assert np.isclose(a.sum() + m.coef_[0][-5], logit_year1)


def test_counterfactual_identity_and_direction(bundle, one):
    p, v = one
    last_sbp = float(v.sbp.iloc[-1])
    same = bundle.counterfactual(p, v, {"sbp": last_sbp}, model="gru")
    assert np.allclose(same["difference"], 0, atol=1e-6)
    cf = bundle.counterfactual(p, v, {"sbp": last_sbp + 40}, model="baseline")
    assert len(cf["changed"]) == 1 and cf["changed"][0]["variable"] == "sbp"
    assert np.all(np.array(cf["difference_lower"]) <= np.array(cf["difference_upper"]) + 1e-12)


def test_counterfactual_does_not_mutate_inputs(bundle, one):
    p, v = one
    before = v.copy()
    bundle.counterfactual(p, v, {"ldl": 2.0, "smoking_current": 0}, model="gru")
    assert v.equals(before)


def test_feature_space_roundtrip(tmp_path, bundle):
    bundle.fs.save(tmp_path / "fs.json")
    fs2 = FeatureSpace.load(tmp_path / "fs.json")
    assert fs2.mean == bundle.fs.mean and fs2.max_len == bundle.fs.max_len


def test_metrics_are_computed_not_hardcoded(pipeline_dirs):
    perf = pipeline_dirs["result"]["performance"]
    m = perf["models"]["gru"]["by_horizon"]["3"]
    assert 0 <= m["auroc"] <= 1 and m["auroc_ci"][0] <= m["auroc"] <= m["auroc_ci"][1] + 1e-9
    assert m["n"] == perf["cohort"]["test"]["known_status_at_primary_horizon"]
    conf = m["confusion"]
    assert conf["tp"] + conf["fp"] + conf["tn"] + conf["fn"] == m["n"]
