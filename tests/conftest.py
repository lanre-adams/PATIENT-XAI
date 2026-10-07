"""Shared fixtures: one small, fast pipeline run per test session (synthetic data only)."""

import pytest

from patientxai.config import PipelineConfig
from patientxai.pipeline import run_pipeline


@pytest.fixture(scope="session")
def pipeline_dirs(tmp_path_factory):
    root = tmp_path_factory.mktemp("px")
    cfg = PipelineConfig.fast(artifacts_dir=root / "artifacts", data_dir=root / "data")
    result = run_pipeline(cfg, log=lambda *_: None)
    return {"root": root, "cfg": cfg, "result": result}


@pytest.fixture(scope="session")
def service(pipeline_dirs):
    from app.service import Service
    r = pipeline_dirs["root"]
    return Service(artifacts_dir=r / "artifacts", data_dir=r / "data", database_url=f"sqlite:///{r / 'test.db'}")


@pytest.fixture(scope="session")
def client(service):
    from fastapi.testclient import TestClient

    from app.main import create_app
    with TestClient(create_app(service)) as c:
        yield c


@pytest.fixture(scope="session")
def test_patient_id(service):
    return service.patients[service.patients.split == "test"].patient_id.iloc[0]
