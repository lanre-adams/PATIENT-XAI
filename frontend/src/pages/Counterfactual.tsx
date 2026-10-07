import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type CounterfactualResponse } from "../lib/api";
import { useApp, useAsync } from "../lib/context";
import { pct, signedPts } from "../lib/format";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { ErrorBox, Loading, NeedPatient } from "../components/Status";

export function CausalNote({ caveat }: { caveat: string }) {
  return (
    <div className="causal-note" role="note">
      <strong>Why this is not proof of causality.</strong> {caveat} The model learned associations from observational
      (synthetic) records. Editing an input asks “what would this model output for a record that looked like this?”,
      not “what would happen to this person if the factor changed?”. Answering the second question needs causal
      assumptions (no unmeasured confounding, correct time ordering, a well-defined intervention) that this demonstrator does not establish.
    </div>
  );
}

export function Counterfactual() {
  const { patientId, model, meta, changes, setChanges } = useApp();
  const detail = useAsync(() => (patientId ? api.patient(patientId) : Promise.resolve(null)), [patientId]);
  const [res, setRes] = useState<CounterfactualResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const current = useMemo(() => {
    const d = detail.data;
    if (!d) return {} as Record<string, number>;
    const out: Record<string, number> = {};
    for (const k of ["sbp", "ldl", "bmi", "hba1c", "activity"]) if (d.latest[k]?.value != null) out[k] = d.latest[k].value as number;
    out.smoking_current = Number(d.patient.smoking_current);
    return out;
  }, [detail.data]);

  useEffect(() => { setRes(null); }, [patientId, model]);
  if (!patientId) return <NeedPatient />;
  if (detail.error) return <ErrorBox error={detail.error} />;
  if (!detail.data || !meta) return <Loading />;

  const run = () => {
    if (!Object.keys(changes).length) return;
    setBusy(true); setErr(null);
    api.counterfactual(patientId, model, changes).then(setRes).catch((e) => setErr(String(e))).finally(() => setBusy(false));
  };
  const cf = res?.counterfactual;
  const gt = res?.simulator_ground_truth;
  const rows = cf ? cf.horizons_years.map((h, i) => ({ h, base: cf.baseline_risk[i], cf: cf.counterfactual_risk[i] })) : [];
  return (
    <>
      <h1>Counterfactual explorer <span className="pid">{patientId}</span></h1>
      <p className="muted">Change modifiable variables at the most recent visit, then re-run the model. Earlier history stays as observed.</p>
      <section className="card">
        <h3>Modifiable synthetic variables</h3>
        <div className="sliders">
          {Object.entries(meta.modifiable).map(([k, m]) => {
            const base = current[k];
            const val = changes[k] ?? base;
            if (k === "smoking_current") {
              return (
                <label key={k} className="slider">
                  <span>{m.label} <span className="muted small">(now: {base ? "yes" : "no"})</span></span>
                  <select value={String(val ?? 0)} onChange={(e) => {
                    const v = Number(e.target.value); const next = { ...changes };
                    if (v === base) delete next[k]; else next[k] = v; setChanges(next);
                  }}><option value="0">No</option><option value="1">Yes</option></select>
                </label>
              );
            }
            if (base === undefined) return null;
            return (
              <label key={k} className="slider">
                <span>{m.label}: <strong>{val}</strong> {m.unit} <span className="muted small">(observed {base})</span></span>
                <input type="range" min={m.min} max={m.max} step={m.step} value={val}
                  onChange={(e) => { const v = Number(e.target.value); const next = { ...changes };
                    if (v === base) delete next[k]; else next[k] = v; setChanges(next); }} />
              </label>
            );
          })}
        </div>
        <div className="row-gap">
          <button className="primary" disabled={busy || !Object.keys(changes).length} onClick={run}>{busy ? "Simulating…" : "Run counterfactual simulation"}</button>
          <button onClick={() => { setChanges({}); setRes(null); }}>Reset</button>
          <span className="muted small">{Object.keys(changes).length} variable(s) changed</span>
        </div>
        {err && <ErrorBox error={err} />}
      </section>

      {cf && gt && res && (
        <>
          <section className="card">
            <h3>Observed vs counterfactual trajectory (model-based)</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--grid)" />
                <XAxis dataKey="h" label={{ value: "Years after index visit", position: "insideBottom", offset: -4 }} />
                <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(v: number) => pct(v)} />
                <Legend verticalAlign="top" height={30} />
                <Line name="Observed record" dataKey="base" stroke="var(--ink)" strokeWidth={2} isAnimationActive={false} />
                <Line name="Edited record" dataKey="cf" stroke="var(--accent)" strokeWidth={2} strokeDasharray="6 4" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
            <div className="table-wrap"><table className="data compact">
              <thead><tr><th>Horizon</th><th>Observed</th><th>Edited</th><th>Absolute diff.</th><th>Relative diff.</th><th>Member range of diff.</th><th>Simulator truth diff.*</th></tr></thead>
              <tbody>{cf.horizons_years.map((h, i) => (
                <tr key={h}><td>{h} y</td><td>{pct(cf.baseline_risk[i])}</td><td>{pct(cf.counterfactual_risk[i])}</td>
                  <td>{signedPts(cf.difference[i])}</td><td>{(100 * cf.relative_difference[i]).toFixed(1)}%</td>
                  <td>{signedPts(cf.difference_lower[i])} to {signedPts(cf.difference_upper[i])}</td>
                  <td>{signedPts(gt.difference[i])}</td></tr>))}</tbody>
            </table></div>
            <p className="small"><strong>Changed factors:</strong> {cf.changed.map((c) => `${c.label} ${c.from ?? "—"} → ${c.to}`).join("; ")}. {cf.scope}</p>
            <p className="small muted">* {gt.note}</p>
          </section>
          <CausalNote caveat={res.caveat} />
          <ExplanationPanel narrative={res.explanation} />
        </>
      )}
      {!res && <CausalNote caveat={meta.counterfactual_caveat} />}
    </>
  );
}
