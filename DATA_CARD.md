# Data card — PATIENT-XAI synthetic cardiometabolic cohort

> **Every record is synthetic.** Identifiers have the form `SYN-#####`. No real person, record,
> registry or dataset was used to generate, calibrate or validate these data.

## Generator
`ml/patientxai/simulate.py`, deterministic given `--seed` (default 20261007), 3,000 patients by default.
Parameters were chosen by the author for plausibility of ranges, **not** fitted to any population.

## Structure
- **Patients:** age at enrolment (30–85), sex, smoking (never/former/current), enrolment date 2015–2022.
- **Visits:** 3–13 per patient at irregular gaps (gamma-distributed, mean ≈ 0.35 years).
  Measured every visit: BMI, SBP, DBP, heart rate, activity (min/week), medication flags.
  Intermittent: HbA1c (≈60% of visits), lipids LDL/HDL (≈50%), synthetic imaging embedding (8-d, ≈30%).
- **Outcome:** synthetic cardiometabolic event in years 1–5 after the last (index) visit, from a known
  discrete-time hazard; independent exponential censoring (mean 10 y) capped at 5 years.

## Causal structure (known by design)
| Variable | Role in simulator |
|---|---|
| Latent state *s*, unmeasured frailty *u* | Drive measurements and outcome; never observed directly |
| SBP, LDL, smoking, activity | **Causal** for the outcome |
| BMI, HbA1c, heart rate, HDL | **Markers** of *s*; predictive but not causal |
| Antihypertensive / statin | Started when readings are high (**confounding by indication**); lower SBP/LDL and therefore risk |
| Imaging embedding | Noisy linear projection of *s*, *u* and age: partial information on *u* |
| Enrolment year | Later cohorts: higher BMI, more statin use (temporal distribution shift) |

## Known limitations
Linear-Gaussian structure is far simpler than real physiology; no measurement-device effects, no coding
practices, no informative visit scheduling, no ethnicity or socioeconomic variables, no competing risks.
Results on these data must not be read as evidence about real populations.

## Licence
Generated data inherit the MIT licence of the code.
