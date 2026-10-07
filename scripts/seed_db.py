"""(Re)seed the database from data/generated/*.csv. Usage: python -m scripts.seed_db"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "ml"), str(ROOT / "backend")]
from app.db import Repository  # noqa: E402
from patientxai.config import PipelineConfig  # noqa: E402

if __name__ == "__main__":
    repo = Repository()
    repo.seed_from_csv(PipelineConfig().data_dir)
    print(f"Seeded {repo.url}")
