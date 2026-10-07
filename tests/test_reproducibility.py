"""Same seed + same config => identical data and identical reported metrics."""

import json

import pytest

from patientxai.config import PipelineConfig
from patientxai.pipeline import run_pipeline

pytestmark = pytest.mark.model


def test_pipeline_is_reproducible(pipeline_dirs, tmp_path):
    cfg = PipelineConfig.fast(artifacts_dir=tmp_path / "a", data_dir=tmp_path / "d")
    again = run_pipeline(cfg, log=lambda *_: None)
    first = pipeline_dirs["result"]
    assert again["manifest"]["data_sha256_16"] == first["manifest"]["data_sha256_16"]
    a = json.dumps(again["performance"], sort_keys=True)
    b = json.dumps(first["performance"], sort_keys=True)
    assert a == b, "metrics changed between two runs with the same seed"
