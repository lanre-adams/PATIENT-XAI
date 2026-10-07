"""Synthetic longitudinal cardiometabolic cohort simulator.

Every value produced here is SYNTHETIC. No record corresponds to a real person.

The simulator is a known structural model, which is what makes it useful for
research: because the data-generating process is known, we can compute the
*true* interventional (do-operator) effect of changing a variable and compare
it with what a purely predictive model "thinks" will happen. Several features
are deliberately built in so that prediction and causation diverge:

* Latent cardiometabolic state ``s`` drives most measurements and the outcome.
* BMI and HbA1c are downstream *markers* of ``s``: they predict the outcome but,
  in this simulator, changing them has no causal effect on risk.
* SBP, LDL, smoking and physical activity are causal.
* Antihypertensive and statin initiation are confounded by indication: they are
  started in people with high readings, so treated people look high-risk even
  though treatment lowers their risk.
* An unmeasured frailty ``u`` affects risk; a synthetic imaging embedding carries
  partial information about it (so multimodal input can help, by construction).
* Visit timing is irregular, laboratory values and imaging are intermittently
  missing, follow-up is right-censored, and later enrolment cohorts drift
  (higher BMI, more statin use) to create temporal distribution shift.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import HORIZONS, IMAGING_DIM

START = pd.Timestamp("2015-01-01")
HAZARD_INTERCEPT = -3.75


@dataclass
class SyntheticCohort:
    patients: pd.DataFrame   # one row per synthetic patient (static + split info)
    visits: pd.DataFrame     # long format, observed values only (NaN where unmeasured)
    outcomes: pd.DataFrame   # event / censoring times after the index visit
    truth: pd.DataFrame      # simulator-only latent parameters (never used as model input)


def _imaging_matrix(rng: np.random.Generator) -> np.ndarray:
    return rng.normal(0, 1, size=(IMAGING_DIM, 3))


def _hazard_logits(truth: dict, years: np.ndarray, *, d_sbp: float = 0.0, d_ldl: float = 0.0,
                   smoking_current: int | None = None, activity: float | None = None) -> np.ndarray:
    """Annual hazard logits for years after index under an optional intervention."""
    cur = truth["smoking_current"] if smoking_current is None else smoking_current
    act = truth["activity_base"] if activity is None else activity
    drift = (0.12 + 0.08 * truth["u"] + 0.15 * cur - 0.12 * (act - 150.0) / 100.0)
    s_y = truth["s_index"] + drift * (years - 0.5)
    age_y = truth["age_index"] + years
    sbp_eff = (126 + 9 * s_y + 0.35 * (age_y - 55) + 2.5 * truth["sex_male"]
               - 12 * truth["antihypertensive_index"] + d_sbp)
    ldl_eff = 3.3 + 0.35 * s_y - 1.1 * truth["statin_index"] + d_ldl
    return (HAZARD_INTERCEPT + 0.55 * s_y + 0.03 * (age_y - 55) + 0.018 * (sbp_eff - 130)
            + 0.35 * (ldl_eff - 3.3) + 0.55 * cur + 0.25 * truth["sex_male"]
            - 0.002 * (act - 150) + 0.35 * truth["u"])


def true_risk_curve(truth: dict, intervention: dict | None = None) -> np.ndarray:
    """Ground-truth cumulative risk at each horizon, optionally under do(intervention).

    ``intervention`` keys mirror the counterfactual explorer and are expressed as new
    target values at the index visit: sbp, ldl, bmi, hba1c, activity, smoking_current,
    antihypertensive.
    BMI and HbA1c are accepted but have no causal effect in this simulator.
    """
    intervention = intervention or {}
    years = np.asarray(HORIZONS, dtype=float)
    kw = {}
    if "sbp" in intervention:
        kw["d_sbp"] = float(intervention["sbp"]) - truth["sbp_index"]
    if "ldl" in intervention:
        kw["d_ldl"] = float(intervention["ldl"]) - truth["ldl_index"]
    if "smoking_current" in intervention:
        kw["smoking_current"] = int(intervention["smoking_current"])
    if "activity" in intervention:
        kw["activity"] = float(intervention["activity"])
    if "antihypertensive" in intervention:  # do(start/stop treatment), effect acts through SBP
        truth = {**truth, "antihypertensive_index": int(intervention["antihypertensive"])}
    h = 1 / (1 + np.exp(-_hazard_logits(truth, years, **kw)))
    return 1 - np.cumprod(1 - h)


def simulate_cohort(n_patients: int = 3000, seed: int = 0) -> SyntheticCohort:
    rng = np.random.default_rng(seed)
    W = _imaging_matrix(rng)
    pat_rows, visit_rows, out_rows, truth_rows = [], [], [], []

    for i in range(n_patients):
        pid = f"SYN-{i:05d}"
        enrol = START + pd.Timedelta(days=float(rng.uniform(0, 8 * 365.25)))
        cohort = enrol.year - 2015
        age0 = float(np.clip(rng.normal(55, 10), 30, 85))
        male = int(rng.random() < 0.5)
        smoke = rng.choice(["never", "former", "current"], p=[0.55, 0.25, 0.20])
        cur = int(smoke == "current")
        u = float(rng.normal())
        act_base = float(np.clip(rng.lognormal(np.log(150), 0.6), 0, 600))
        drift = 0.12 + 0.08 * u + 0.15 * cur - 0.12 * (act_base - 150) / 100
        s0 = 0.6 * u + 0.03 * (age0 - 55) + rng.normal(0, 0.4)

        n_vis = int(rng.integers(3, 14))
        gaps = rng.gamma(2.0, 0.15, size=n_vis - 1) + 0.05
        times = np.concatenate([[0.0], np.cumsum(gaps)])
        walk = np.concatenate([[0.0], np.cumsum(rng.normal(0, 0.1 * np.sqrt(gaps)))])
        on_ah = on_st = 0
        last = {}
        for j, t in enumerate(times):
            s_t = s0 + drift * t + walk[j]
            age = age0 + t
            act = float(np.clip(act_base * np.exp(rng.normal(0, 0.25)), 0, 900))
            bmi = 27 + 2.2 * s_t + 0.15 * cohort + rng.normal(0, 0.7)
            sbp = 126 + 9 * s_t + 0.35 * (age - 55) + 2.5 * male - 12 * on_ah + rng.normal(0, 7)
            dbp = 0.5 * sbp + 14 + rng.normal(0, 5)
            hr = 71 + 2.5 * s_t - 0.01 * (act - 150) + rng.normal(0, 6)
            hba1c = 5.5 + 0.4 * s_t + 0.03 * (bmi - 27) + rng.normal(0, 0.25)
            ldl = 3.3 + 0.35 * s_t - 1.1 * on_st + rng.normal(0, 0.45)
            hdl = 1.35 - 0.08 * s_t + 0.0006 * (act - 150) - 0.12 * male + rng.normal(0, 0.15)
            emb = W @ np.array([s_t, u, (age - 55) / 10]) + rng.normal(0, 0.6, IMAGING_DIM)
            hb_obs = rng.random() < 0.6 or j == 0
            lip_obs = rng.random() < 0.5 or j == 0
            img_obs = rng.random() < 0.3
            row = {
                "patient_id": pid, "visit_index": j,
                "visit_date": (enrol + pd.Timedelta(days=float(t * 365.25))).date().isoformat(),
                "t_years": round(float(t), 4), "age": round(age, 1), "bmi": round(bmi, 1),
                "sbp": round(sbp), "dbp": round(dbp), "heart_rate": round(hr),
                "hba1c": round(hba1c, 2) if hb_obs else np.nan,
                "ldl": round(ldl, 2) if lip_obs else np.nan,
                "hdl": round(hdl, 2) if lip_obs else np.nan,
                "activity": round(act), "antihypertensive": on_ah, "statin": on_st,
                "hba1c_observed": int(hb_obs), "lipids_observed": int(lip_obs),
                "imaging_observed": int(img_obs),
            }
            for k in range(IMAGING_DIM):
                row[f"img_{k}"] = round(float(emb[k]), 3) if img_obs else np.nan
            visit_rows.append(row)
            last = dict(s=s0 + drift * t + walk[j], age=age, sbp=sbp, ldl=ldl)
            # Treatment decisions after the measurement (confounding by indication).
            if not on_ah and sbp > 140 and rng.random() < 0.45:
                on_ah = 1
            if not on_st and ((ldl > 4.0 and rng.random() < 0.35) or rng.random() < 0.03 * cohort):
                on_st = 1
        # Medication status at the index visit is that recorded at the last visit.
        ah_idx = visit_rows[-1]["antihypertensive"]
        st_idx = visit_rows[-1]["statin"]
        truth = dict(patient_id=pid, u=u, drift=drift, s_index=last["s"], age_index=last["age"],
                     sex_male=male, smoking_current=cur, activity_base=act_base,
                     antihypertensive_index=ah_idx, statin_index=st_idx,
                     sbp_index=float(visit_rows[-1]["sbp"]), ldl_index=float(last["ldl"]))
        years = np.asarray(HORIZONS, dtype=float)
        h = 1 / (1 + np.exp(-_hazard_logits(truth, years)))
        event_time = np.nan
        for y, hy in zip(HORIZONS, h, strict=True):
            if rng.random() < hy:
                event_time = (y - 1) + float(rng.random())
                break
        censor_time = float(min(rng.exponential(10.0), 5.0))
        observed = bool(not np.isnan(event_time) and event_time <= censor_time)
        follow = event_time if observed else censor_time

        index_date = visit_rows[-1]["visit_date"]
        pat_rows.append(dict(
            patient_id=pid, enrol_date=enrol.date().isoformat(), enrol_year=enrol.year,
            index_date=index_date, sex="M" if male else "F", sex_male=male,
            smoking_status=smoke, smoking_current=cur, smoking_former=int(smoke == "former"),
            n_visits=n_vis, age_at_index=round(last["age"], 1)))
        out_rows.append(dict(patient_id=pid, event=int(observed), time=round(float(follow), 4),
                             censor_time=round(censor_time, 4),
                             true_event_time=None if np.isnan(event_time) else round(event_time, 4)))
        truth_rows.append(truth)

    patients = pd.DataFrame(pat_rows)
    return SyntheticCohort(patients=patients, visits=pd.DataFrame(visit_rows),
                           outcomes=pd.DataFrame(out_rows), truth=pd.DataFrame(truth_rows))


def assign_split(patients: pd.DataFrame, train_until: int, val_year: int) -> pd.Series:
    """Temporal split by enrolment year (train on earlier cohorts, test on later ones)."""
    return np.where(patients.enrol_year <= train_until, "train",
                    np.where(patients.enrol_year == val_year, "val", "test"))


def horizon_label(outcomes: pd.DataFrame, k: float) -> pd.Series:
    """1 = event by k years; 0 = followed >= k years event-free; NaN = censored before k."""
    lab = pd.Series(np.nan, index=outcomes.index)
    lab[(outcomes.event == 1) & (outcomes.time <= k)] = 1.0
    lab[(outcomes.time >= k) & ~((outcomes.event == 1) & (outcomes.time <= k))] = 0.0
    return lab
