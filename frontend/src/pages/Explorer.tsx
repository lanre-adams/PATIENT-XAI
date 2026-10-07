import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useApp, useAsync } from "../lib/context";
import { num } from "../lib/format";
import { ErrorBox, Loading, NeedPatient } from "../components/Status";

const SERIES = [
  { key: "sbp", label: "Systolic BP (mmHg)" }, { key: "dbp", label: "Diastolic BP (mmHg)" },
  { key: "bmi", label: "BMI (kg/m²)" }, { key: "hba1c", label: "HbA1c (%)" },
  { key: "ldl", label: "LDL (mmol/L)" }, { key: "heart_rate", label: "Heart rate (bpm)" },
  { key: "activity", label: "Activity (min/week)" },
];

export function Explorer() {
  const { patientId } = useApp();
  const [series, setSeries] = useState("sbp");
  const { data, error, loading } = useAsync(() => (patientId ? api.patient(patientId) : Promise.resolve(null)), [patientId]);
  const sim = useAsync(() => (patientId ? api.similar(patientId, 10) : Promise.resolve(null)), [patientId]);
  if (!patientId) return <NeedPatient />;
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return <Loading />;
  const p = data.patient;
  const s = SERIES.find((x) => x.key === series)!;
  const points = data.visits.map((v) => ({ t: Number(v.t_years.toFixed(2)), date: v.visit_date, value: v[series] }));
  return (
    <>
      <h1>Synthetic patient explorer <span className="pid">{p.patient_id}</span></h1>
      <div className="facts">
        <span>Sex {p.sex}</span><span>Age at index {num(Number(p.age_at_index), 0)}</span>
        <span>Smoking {String(p.smoking_status)}</span><span>{data.visits.length} visits</span>
        <span>Enrolled {String(p.enrol_date)}</span><span>Cohort: {String(p.split)}</span>
      </div>

      <section className="card">
        <h3>Latest measurements</h3>
        <div className="tiles">
          {Object.entries(data.latest).map(([k, m]) => (
            <div className="tile" key={k}>
              <div className="tile-label">{m.label}</div>
              <div className="tile-value">{k === "antihypertensive" || k === "statin" ? (m.value ? "Yes" : "No") : num(m.value, k === "hba1c" || k === "ldl" || k === "hdl" ? 2 : 0)}
                <span className="unit">{m.unit}</span></div>
              <div className="tile-date muted">{m.date ?? "never measured"}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Longitudinal trajectory</h3>
          <select aria-label="Measurement" value={series} onChange={(e) => setSeries(e.target.value)}>
            {SERIES.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} label={{ value: "Years since first visit", position: "insideBottom", offset: -4 }} />
            <YAxis domain={["auto", "auto"]} />
            <Tooltip formatter={(v) => (v === null ? "not measured" : v)} labelFormatter={(t) => `Year ${t}`} />
            <Legend verticalAlign="top" height={30} />
            <Line name={s.label} dataKey="value" stroke="var(--ink)" strokeWidth={2} connectNulls dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
        <p className="muted small">Gaps between dots reflect irregular visit timing. Labs that were not measured at a visit are bridged (not imputed) in this chart.</p>
      </section>

      <section className="card">
        <h3>Visit timeline</h3>
        <div className="table-wrap">
          <table className="data compact">
            <thead><tr><th>#</th><th>Date</th><th>Age</th><th>SBP/DBP</th><th>HR</th><th>BMI</th><th>HbA1c</th><th>LDL</th><th>HDL</th><th>Activity</th><th>Anti-HT</th><th>Statin</th><th>Imaging</th></tr></thead>
            <tbody>{data.visits.map((v) => (
              <tr key={v.visit_index}>
                <td>{v.visit_index + 1}</td><td>{v.visit_date}</td><td>{num(v.age as number, 1)}</td>
                <td>{v.sbp}/{v.dbp}</td><td>{v.heart_rate}</td><td>{num(v.bmi as number, 1)}</td>
                <td>{num(v.hba1c as number | null)}</td><td>{num(v.ldl as number | null)}</td><td>{num(v.hdl as number | null)}</td>
                <td>{v.activity}</td><td>{v.antihypertensive ? "●" : ""}</td><td>{v.statin ? "●" : ""}</td><td>{v.imaging_observed ? "●" : ""}</td>
              </tr>))}</tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>How does this trajectory compare with similar synthetic subjects?</h3>
        {sim.data ? (
          <>
            <p>Nearest {sim.data.neighbours.length} training-cohort patients in the GRU latent space ({sim.data.space}).
              Observed {""}synthetic event rate by year 3 among the {sim.data.n_with_known_status} with known status:{" "}
              <strong>{sim.data.observed_event_rate_by_primary_horizon === null ? "—" : `${(100 * sim.data.observed_event_rate_by_primary_horizon).toFixed(0)}%`}</strong>;
              this patient's model estimate: <strong>{(100 * sim.data.this_patient_predicted_risk).toFixed(1)}%</strong>.</p>
            <p className="muted small">Ten neighbours give a very noisy rate. This is a sanity check on the representation, not a second prediction.</p>
            <div className="chips">{sim.data.neighbours.map((n) => (
              <span key={n.patient_id} className={`chip ${n.event ? "chip-event" : ""}`}>{n.patient_id} · sim {n.similarity.toFixed(2)}{n.event ? " · event" : ""}</span>
            ))}</div>
          </>
        ) : sim.error ? <ErrorBox error={sim.error} /> : <Loading />}
      </section>

      <details className="card">
        <summary>Observed synthetic outcome (hidden from the model)</summary>
        <p>{data.observed_outcome.event ? `Synthetic event at ${data.observed_outcome.follow_up_years.toFixed(2)} years after the index visit.`
          : `No synthetic event; followed for ${data.observed_outcome.follow_up_years.toFixed(2)} years (censored).`}</p>
        <p className="muted small">{data.observed_outcome.note}</p>
      </details>
    </>
  );
}
