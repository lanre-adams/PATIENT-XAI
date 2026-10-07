import { useEffect, useState } from "react";
import { api, type PatientSummary } from "../lib/api";
import { useApp } from "../lib/context";

export function PatientPicker() {
  const { patientId, setPatientId } = useApp();
  const [split, setSplit] = useState("test");
  const [items, setItems] = useState<PatientSummary[]>([]);
  useEffect(() => { api.patients(split, undefined, 300).then((r) => setItems(r.items)).catch(() => setItems([])); }, [split]);
  return (
    <div className="picker">
      <label>Cohort
        <select value={split} onChange={(e) => setSplit(e.target.value)} aria-label="Cohort split">
          <option value="test">Test (2021–22, held out)</option>
          <option value="val">Validation (2020)</option>
          <option value="train">Training (2015–19)</option>
        </select>
      </label>
      <label>Synthetic patient
        <select value={patientId} onChange={(e) => setPatientId(e.target.value)} aria-label="Synthetic patient">
          {patientId && !items.some((i) => i.patient_id === patientId) && <option value={patientId}>{patientId}</option>}
          {items.map((p) => (
            <option key={p.patient_id} value={p.patient_id}>
              {p.patient_id} · {p.sex} · {Math.round(p.age_at_index)}y · {p.n_visits} visits
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export function ModelToggle() {
  const { model, setModel } = useApp();
  return (
    <div className="toggle" role="radiogroup" aria-label="Model">
      {(["gru", "baseline"] as const).map((m) => (
        <button key={m} role="radio" aria-checked={model === m} className={model === m ? "on" : ""} onClick={() => setModel(m)}>
          {m === "gru" ? "GRU ensemble" : "Logistic baseline"}
        </button>
      ))}
    </div>
  );
}
