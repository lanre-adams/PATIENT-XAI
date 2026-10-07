"""The Explanation Engine must separate prediction / association / uncertainty /
counterfactual / causality and must never emit treatment advice."""

import pytest

from patientxai import COUNTERFACTUAL_CAVEAT
from patientxai.explanation_engine import contains_forbidden


@pytest.fixture(scope="module")
def cf_result(service, test_patient_id):
    return service.counterfactual(test_patient_id, "gru", {"sbp": 120, "smoking_current": 0})


def test_all_five_concepts_present(cf_result):
    pl = cf_result["explanation"]["plain_language"]
    for key in ["prediction", "association", "uncertainty", "counterfactual", "causality", "disclaimer"]:
        assert pl[key], key
    assert "not be interpreted as clinical causes" in pl["association"]
    assert COUNTERFACTUAL_CAVEAT in pl["counterfactual"]


def test_no_medical_advice(cf_result, service, test_patient_id):
    texts = list(cf_result["explanation"]["plain_language"].values()) + cf_result["explanation"]["technical"]
    pred = service.predict(test_patient_id, "baseline")
    texts += list(pred["explanation"]["plain_language"].values()) + pred["explanation"]["technical"]
    for t in texts:
        if t:
            assert contains_forbidden(t) == [], t


def test_technical_includes_calibration_caveat(cf_result):
    assert any("Calibration caveat" in t for t in cf_result["explanation"]["technical"])
