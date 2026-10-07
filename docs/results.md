# Results (generated)

Generated from `artifacts/` by `scripts/write_results.py`. Run created 2026-10-07T14:28:29+00:00, model version `patientxai-0.1.0-mvp`, pipeline runtime 250.8 s. Data hash (visits) `3f3c821ebe789992`.

**All results are on SYNTHETIC data from a known simulator. They demonstrate the pipeline, not clinical performance.**

## Cohort

| Split | Enrolment years | Patients | Observed events | Known status at 3 y |
|---|---|---|---|---|
| train | 2015, 2016, 2017, 2018, 2019 | 1915 | 411 | 1434 |
| val | 2020 | 348 | 87 | 271 |
| test | 2021, 2022 | 737 | 176 | 564 |

## Test-cohort performance at 3 years

| Model | AUROC (95% CI) | AUPRC (95% CI) | Brier | ECE | Cal. slope | Cal. intercept | Sens. | Spec. |
|---|---|---|---|---|---|---|---|---|
| Discrete-time logistic regression (baseline) | 0.848 (0.810–0.884) | 0.602 (0.511–0.696) | 0.118 | 0.032 | 1.03 | +0.08 | 0.75 | 0.77 |
| GRU deep ensemble (longitudinal) | 0.843 (0.801–0.881) | 0.583 (0.480–0.684) | 0.120 | 0.045 | 0.94 | -0.09 | 0.81 | 0.73 |
| GRU ensemble without imaging (ablation) | 0.846 (0.809–0.879) | 0.588 (0.491–0.684) | 0.119 | 0.027 | 1.00 | -0.03 | 0.73 | 0.77 |

AUROC by horizon (years 1–5):

- Discrete-time logistic regression (baseline): 1y 0.843, 2y 0.840, 3y 0.848, 4y 0.843, 5y 0.833
- GRU deep ensemble (longitudinal): 1y 0.837, 2y 0.835, 3y 0.843, 4y 0.838, 5y 0.843
- GRU ensemble without imaging (ablation): 1y 0.832, 2y 0.840, 3y 0.846, 4y 0.839, 5y 0.848

## Subgroups (sex), 3-year horizon

| Model | Group | n | Observed | Mean predicted | AUROC |
|---|---|---|---|---|---|
| Discrete-time logistic regression (baseline) | F | 281 | 0.181 | 0.189 | 0.870 |
| Discrete-time logistic regression (baseline) | M | 283 | 0.230 | 0.210 | 0.830 |
| GRU deep ensemble (longitudinal) | F | 281 | 0.181 | 0.204 | 0.856 |
| GRU deep ensemble (longitudinal) | M | 283 | 0.230 | 0.215 | 0.835 |
| GRU ensemble without imaging (ablation) | F | 281 | 0.181 | 0.205 | 0.859 |
| GRU ensemble without imaging (ablation) | M | 283 | 0.230 | 0.212 | 0.839 |

## Counterfactual audit (3-year risk, 150 sampled test patients)

| Intervention | n | Causal in simulator | True mean change | GRU simulated | Baseline simulated | GRU–truth r | Sign agreement |
|---|---|---|---|---|---|---|---|
| Lower SBP by 20 mmHg | 150 | yes | -3.4 pts | -2.1 pts | -0.2 pts | 0.76 | 100% |
| Lower LDL by 1.0 mmol/L | 150 | yes | -3.3 pts | -0.7 pts | +1.0 pts | 0.33 | 77% |
| Increase activity by 150 min/week | 150 | yes | -5.1 pts | -2.0 pts | -4.5 pts | 0.74 | 99% |
| Stop smoking (current smokers) | 33 | yes | -6.6 pts | -3.0 pts | -6.7 pts | 0.97 | 100% |
| Lower BMI by 3 kg/m² | 150 | no (marker) | +0.0 pts | -2.6 pts | -4.2 pts | n/a | n/a |
| Lower HbA1c by 0.8% | 150 | no (marker) | +0.0 pts | -3.0 pts | -4.3 pts | n/a | n/a |
| Set antihypertensive flag to 1 (no other change) | 150 | yes | -1.3 pts | +0.5 pts | +1.1 pts | -0.84 | 24% |
