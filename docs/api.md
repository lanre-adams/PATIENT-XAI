# API reference (summary — full OpenAPI at http://localhost:8000/docs)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness, version, disclaimer |
| GET | `/api/meta` | model version, horizons, modifiable variables and ranges, cohort counts |
| GET | `/api/patients?split=&q=&limit=&offset=` | list synthetic patients |
| GET | `/api/patients/{id}` | visits, latest measurements, observed synthetic outcome |
| GET | `/api/predict/{id}?model=gru\|baseline` | 1–5-year risk, uncertainty interval, Explanation Engine output |
| GET | `/api/explain/{id}?model=&horizon=` | feature and temporal attributions + narratives |
| POST | `/api/counterfactual` | `{patient_id, model, changes}` → model-based simulation, paired uncertainty, simulator ground truth |
| GET | `/api/similar/{id}?k=` | nearest training patients in GRU latent space |
| GET | `/api/performance` | test-cohort metrics, subgroup table, counterfactual audit |
| POST | `/api/report` | `{patient_id, model, format: html\|pdf\|json, changes?}` → Trustworthy AI report |

Validation: model keys are an enum; `changes` keys must be in the modifiable list and inside the documented
ranges (422 otherwise); patient ids must match `SYN-#####`. All responses carry `X-Research-Demonstrator`.
