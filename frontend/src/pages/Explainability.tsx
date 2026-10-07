import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useApp, useAsync } from "../lib/context";
import { num } from "../lib/format";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { ErrorBox, Loading, NeedPatient } from "../components/Status";

export function Explainability() {
  const { patientId, model } = useApp();
  const [h, setH] = useState(3);
  const { data, error, loading } = useAsync(() => (patientId ? api.explain(patientId, model, h) : Promise.resolve(null)), [patientId, model, h]);
  if (!patientId) return <NeedPatient />;
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return <Loading what="Computing attributions" />;
  const a = data.attribution;
  const top = a.contributions.slice(0, 12).map((c) => ({ ...c, name: c.label })).reverse();
  return (
    <>
      <h1>Explainability <span className="pid">{patientId}</span></h1>
      <div className="card-head">
        <p className="muted">{a.method}. Units: <strong>{a.units}</strong>.</p>
        <label>Horizon&nbsp;
          <select value={h} onChange={(e) => setH(Number(e.target.value))} aria-label="Horizon">
            {[1, 2, 3, 4, 5].map((x) => <option key={x} value={x}>{x} year{x > 1 ? "s" : ""}</option>)}
          </select>
        </label>
      </div>
      <section className="card">
        <h3>Strongest contributing factors</h3>
        <ResponsiveContainer width="100%" height={Math.max(260, top.length * 30)}>
          <BarChart data={top} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => v.toFixed(3)} />
            <YAxis type="category" dataKey="name" width={250} tick={{ fontSize: 12 }} />
            <ReferenceLine x={0} stroke="var(--ink)" />
            <Tooltip formatter={(v: number) => v.toFixed(4)} />
            <Bar dataKey="contribution" isAnimationActive={false}>
              {top.map((c) => <Cell key={c.feature} fill={c.contribution > 0 ? "var(--up)" : "var(--down)"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="small"><span className="swatch up" /> raises the model's estimate &nbsp; <span className="swatch down" /> lowers it.
          Direction describes the model, not the body.</p>
        <div className="table-wrap"><table className="data compact">
          <thead><tr><th>Feature</th><th>Latest value</th><th>Contribution</th><th>Direction</th></tr></thead>
          <tbody>{a.contributions.slice(0, 10).map((c) => (
            <tr key={c.feature}><td>{c.label}</td><td>{num(c.value)}</td><td>{c.contribution.toFixed(4)}</td><td>{c.direction}</td></tr>
          ))}</tbody></table></div>
        {a.completeness && (
          <p className="small muted">Completeness check: attributions sum to {a.completeness.sum_attributions.toFixed(4)};
            f(x) − f(baseline) = {a.completeness.f_x_minus_f_baseline.toFixed(4)} (gap {a.completeness.gap.toFixed(4)}).
            A small gap means the integral was approximated well — not that the explanation is correct about the world.</p>
        )}
      </section>
      {a.temporal && (
        <section className="card">
          <h3>Temporal importance — which visits mattered</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={a.temporal.map((t) => ({ ...t, label: `#${t.visit_index + 1}` }))}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="label" />
              <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip formatter={(v: number) => `${(100 * v).toFixed(1)}%`} labelFormatter={(l, p) => `${l} ${p?.[0]?.payload?.visit_date ?? ""}`} />
              <Bar dataKey="share" name="Share of absolute attribution" fill="var(--ink)" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <p className="muted small">Share of total absolute integrated-gradient attribution falling on each visit. Recurrent models often concentrate on recent visits; whether that is clinically appropriate is a research question.</p>
        </section>
      )}
      {!a.temporal && <p className="muted">The baseline summarises history into last values and trends, so per-visit attribution is not defined. Switch to the GRU ensemble for temporal importance.</p>}
      <ExplanationPanel narrative={data.explanation} />
    </>
  );
}
