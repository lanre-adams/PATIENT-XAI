// Typed client for the PATIENT-XAI API. All data are SYNTHETIC.
export type ModelKey = "gru" | "baseline";

export interface Meta {
  name: string; model_version: string; disclaimer: string; counterfactual_caveat: string;
  dataset_type: string; created_utc: string; horizons_years: number[]; primary_horizon: number;
  models: Record<ModelKey, string>;
  modifiable: Record<string, { min: number; max: number; step: number; label: string; unit: string }>;
  cohort_counts: Record<string, number>; n_gru_members: number;
}
export interface PatientSummary {
  patient_id: string; sex: string; age_at_index: number; n_visits: number;
  smoking_status: string; split: string; enrol_year: number;
}
export interface Visit { [k: string]: number | string | null; visit_index: number; visit_date: string; t_years: number }
export interface PatientDetail {
  patient: Record<string, string | number>; visits: Visit[];
  latest: Record<string, { value: number | null; label: string; unit: string; date: string | null }>;
  observed_outcome: { event: number; follow_up_years: number; note: string };
}
export interface Prediction {
  model: ModelKey; model_name: string; horizons_years: number[]; risk: number[]; lower: number[];
  upper: number[]; member_std: number[]; n_members: number; uncertainty_method: string; primary_horizon: number;
}
export interface Narrative {
  technical: string[];
  plain_language: Record<"prediction" | "association" | "uncertainty" | "counterfactual" | "causality" | "disclaimer", string | null>;
}
export interface Contribution { feature: string; label: string; contribution: number; direction: string; value: number | null }
export interface Attribution {
  model: ModelKey; horizon_years: number; method: string; units: string; contributions: Contribution[];
  temporal: { visit_index: number; visit_date: string; signed: number; share: number }[] | null;
  completeness: { sum_attributions: number; f_x_minus_f_baseline: number; gap: number } | null;
}
export interface Counterfactual {
  horizons_years: number[]; changed: { variable: string; label: string; from: number | null; to: number }[];
  baseline_risk: number[]; counterfactual_risk: number[]; difference: number[]; relative_difference: number[];
  difference_lower: number[]; difference_upper: number[]; scope: string;
}
export interface CounterfactualResponse {
  counterfactual: Counterfactual; explanation: Narrative; caveat: string;
  simulator_ground_truth: { baseline_risk: number[]; counterfactual_risk: number[]; difference: number[]; note: string };
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`${r.status}: ${body.slice(0, 300)}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  meta: () => http<Meta>("/meta"),
  patients: (split?: string, q?: string, limit = 200) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (split) p.set("split", split);
    if (q) p.set("q", q);
    return http<{ total: number; items: PatientSummary[] }>(`/patients?${p}`);
  },
  patient: (id: string) => http<PatientDetail>(`/patients/${id}`),
  predict: (id: string, model: ModelKey) =>
    http<{ prediction: Prediction; explanation: Narrative }>(`/predict/${id}?model=${model}`),
  explain: (id: string, model: ModelKey, horizon: number) =>
    http<{ attribution: Attribution; explanation: Narrative }>(`/explain/${id}?model=${model}&horizon=${horizon}`),
  counterfactual: (patient_id: string, model: ModelKey, changes: Record<string, number>) =>
    http<CounterfactualResponse>("/counterfactual", { method: "POST", body: JSON.stringify({ patient_id, model, changes }) }),
  similar: (id: string, k = 10) => http<{
    neighbours: { patient_id: string; similarity: number; event: number; follow_up_years: number }[];
    observed_event_rate_by_primary_horizon: number | null; n_with_known_status: number; space: string;
    this_patient_predicted_risk: number;
  }>(`/similar/${id}?k=${k}`),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  performance: () => http<{ performance: any; counterfactual_audit: any }>("/performance"),
  report: async (patient_id: string, model: ModelKey, format: "html" | "pdf" | "json", changes?: Record<string, number>) => {
    const r = await fetch("/api/report", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id, model, format, changes: changes && Object.keys(changes).length ? changes : null }),
    });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.blob();
  },
};
