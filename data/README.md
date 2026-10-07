# data/

`data/generated/` is created by `python -m scripts.run_pipeline` and is git-ignored.
It contains **only synthetic records** produced by `ml/patientxai/simulate.py`:

| File | Content |
|---|---|
| `patients.csv` | one row per synthetic patient (static variables, enrolment year, split) |
| `visits.csv` | long-format visits; unmeasured labs/imaging are blank |
| `outcomes.csv` | event indicator and follow-up time after the index visit |
| `simulator_truth.csv` | latent simulator parameters. **Never used as model input**; used only to compute ground-truth interventional effects for the counterfactual audit |

`patientxai.db` (SQLite) is seeded from these CSVs on first API start.
No file in this repository contains or was derived from real patient data. See `DATA_CARD.md`.
