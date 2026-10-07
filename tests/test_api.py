"""Integration tests for the HTTP API (FastAPI TestClient, synthetic data)."""

import pytest

pytestmark = pytest.mark.integration


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.headers["X-Research-Demonstrator"].startswith("not-a-medical-device")


def test_meta_has_disclaimer_and_modifiables(client):
    m = client.get("/api/meta").json()
    assert "Not a medical device" in m["disclaimer"]
    assert "sbp" in m["modifiable"] and m["primary_horizon"] == 3
    assert "SYNTHETIC" in m["dataset_type"]


def test_patient_list_and_detail(client, test_patient_id):
    lst = client.get("/api/patients", params={"split": "test", "limit": 5}).json()
    assert lst["total"] > 0 and len(lst["items"]) <= 5
    d = client.get(f"/api/patients/{test_patient_id}").json()
    assert len(d["visits"]) >= 3 and "sbp" in d["latest"]


def test_unknown_patient_404(client):
    assert client.get("/api/patients/SYN-99999").status_code == 404
    assert client.get("/api/predict/SYN-99999").status_code == 404


@pytest.mark.parametrize("model", ["gru", "baseline"])
def test_predict(client, test_patient_id, model):
    r = client.get(f"/api/predict/{test_patient_id}", params={"model": model})
    assert r.status_code == 200
    body = r.json()
    assert len(body["prediction"]["risk"]) == 5
    assert body["explanation"]["technical"] and body["explanation"]["plain_language"]["prediction"]


def test_invalid_model_rejected(client, test_patient_id):
    assert client.get(f"/api/predict/{test_patient_id}", params={"model": "oracle"}).status_code == 422


def test_explain_endpoint(client, test_patient_id):
    r = client.get(f"/api/explain/{test_patient_id}", params={"model": "gru", "horizon": 2})
    assert r.status_code == 200
    a = r.json()["attribution"]
    assert a["horizon_years"] == 2 and a["contributions"] and a["temporal"]
    assert client.get(f"/api/explain/{test_patient_id}", params={"horizon": 9}).status_code == 422


def test_counterfactual_endpoint(client, test_patient_id):
    r = client.post("/api/counterfactual", json={"patient_id": test_patient_id, "model": "gru",
                                                  "changes": {"sbp": 118, "activity": 300}})
    assert r.status_code == 200
    b = r.json()
    assert len(b["counterfactual"]["difference"]) == 5
    assert "do not establish" in b["caveat"]
    assert "synthetic" in b["simulator_ground_truth"]["note"].lower()


@pytest.mark.parametrize("changes", [{"insulin": 1}, {"sbp": 400}, {"smoking_current": 0.5}, {}])
def test_counterfactual_validation(client, test_patient_id, changes):
    r = client.post("/api/counterfactual", json={"patient_id": test_patient_id, "changes": changes})
    assert r.status_code == 422


def test_counterfactual_rejects_malformed_id(client):
    r = client.post("/api/counterfactual", json={"patient_id": "../etc", "changes": {"sbp": 120}})
    assert r.status_code == 422


def test_similar(client, test_patient_id):
    b = client.get(f"/api/similar/{test_patient_id}", params={"k": 5}).json()
    assert len(b["neighbours"]) == 5 and all(n["patient_id"] != test_patient_id for n in b["neighbours"])


def test_performance(client):
    b = client.get("/api/performance").json()
    assert set(b["performance"]["models"]) >= {"gru", "baseline", "gru_no_imaging"}
    assert b["counterfactual_audit"]["interventions"]


@pytest.mark.parametrize("fmt,ctype", [("html", "text/html"), ("pdf", "application/pdf"),
                                       ("json", "application/json")])
def test_report_generation(client, test_patient_id, fmt, ctype):
    r = client.post("/api/report", json={"patient_id": test_patient_id, "format": fmt,
                                         "changes": {"ldl": 2.5}})
    assert r.status_code == 200 and r.headers["content-type"].startswith(ctype)
    if fmt == "pdf":
        assert r.content[:4] == b"%PDF"
    if fmt == "html":
        for field in ["Sample identifier", "Model version", "Timestamp", "Known limitations",
                      "Not a medical device", "Counterfactual result"]:
            assert field in r.text
    if fmt == "json":
        j = r.json()
        for key in ["patient_id", "model", "prediction", "uncertainty", "important_features",
                    "counterfactual", "known_limitations", "dataset_type", "model_version", "timestamp_utc"]:
            assert key in j


def test_requests_are_logged(service, client, test_patient_id):
    n0 = service.repo.log_count()
    client.get(f"/api/predict/{test_patient_id}")
    assert service.repo.log_count() == n0 + 1
