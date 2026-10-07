"""Generate synthetic data, train, evaluate and save artifacts.

Usage:
    python -m scripts.run_pipeline            # full configuration (~2-6 min on a laptop CPU)
    python -m scripts.run_pipeline --fast     # small configuration used by tests
    python -m scripts.run_pipeline --n-patients 5000 --seed 7
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))

from patientxai.config import PipelineConfig  # noqa: E402
from patientxai.pipeline import run_pipeline  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--n-patients", type=int)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args(argv)
    cfg = PipelineConfig.fast() if a.fast else PipelineConfig()
    if a.n_patients:
        cfg.n_patients = a.n_patients
    if a.seed is not None:
        cfg.seed = a.seed
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
