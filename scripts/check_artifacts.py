"""Exit 0 if trained artifacts exist (used by the Docker entrypoint)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from patientxai.config import PipelineConfig  # noqa: E402

need = ["feature_space.json", "baseline.joblib", "gru_ensemble.pt", "performance.json",
        "counterfactual_audit.json", "manifest.json"]
d = PipelineConfig().artifacts_dir
missing = [n for n in need if not (d / n).exists()]
print("artifacts ok" if not missing else f"missing: {missing}")
sys.exit(1 if missing else 0)
