"""Persistence layer (SQLAlchemy Core).

SQLite is the default for the MVP. Because all access goes through SQLAlchemy and
this small repository class, switching to PostgreSQL is a configuration change:
set DATABASE_URL=postgresql+psycopg://user:pass@host/db and install the driver.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, inspect, select, text

metadata = MetaData()

prediction_log = Table(
    "prediction_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_utc", DateTime, nullable=False),
    Column("patient_id", String(32), nullable=False),
    Column("model", String(32), nullable=False),
    Column("model_version", String(64), nullable=False),
    Column("kind", String(32), nullable=False),  # predict | counterfactual | report
    Column("payload", Text, nullable=False),
)

DATA_TABLES = ["patients", "visits", "outcomes", "simulator_truth"]


def default_url() -> str:
    root = Path(__file__).resolve().parents[2]
    return os.environ.get("DATABASE_URL", f"sqlite:///{root / 'data' / 'patientxai.db'}")


class Repository:
    def __init__(self, url: str | None = None):
        self.url = url or default_url()
        if self.url.startswith("sqlite:///"):
            Path(self.url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(self.url, future=True)
        metadata.create_all(self.engine)

    def is_seeded(self) -> bool:
        insp = inspect(self.engine)
        if not all(insp.has_table(t) for t in DATA_TABLES):
            return False
        with self.engine.connect() as c:
            return c.execute(text("SELECT COUNT(*) FROM patients")).scalar() > 0

    def seed_from_csv(self, data_dir: Path) -> None:
        for t in DATA_TABLES:
            df = pd.read_csv(Path(data_dir) / f"{t}.csv")
            df.to_sql(t, self.engine, if_exists="replace", index=False)

    def frame(self, table: str) -> pd.DataFrame:
        if table not in DATA_TABLES:
            raise ValueError(table)
        return pd.read_sql_table(table, self.engine)

    def log(self, patient_id: str, model: str, model_version: str, kind: str, payload: dict) -> None:
        with self.engine.begin() as c:
            c.execute(prediction_log.insert().values(
                created_utc=datetime.now(timezone.utc).replace(tzinfo=None), patient_id=patient_id,
                model=model, model_version=model_version, kind=kind, payload=json.dumps(payload)[:20000]))

    def log_count(self) -> int:
        with self.engine.connect() as c:
            return len(c.execute(select(prediction_log.c.id)).all())
