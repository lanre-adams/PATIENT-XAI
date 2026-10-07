import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useApp, useAsync } from "../lib/context";
import { pct, riskBand } from "../lib/format";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { ErrorBox, Loading, NeedPatient } from "../components/Status";
import { DisclaimerBanner } from "../components/DisclaimerBanner";

export function Prediction() {
  const { patientId, model } = useApp();
  const { data, error, loading } = useAsync(() => (patientId ? api.predict(patientId, model) : Promise.resolve(null)), [patientId, model]);
  if (!patientId) return <NeedPatient />;
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return <Loading what="Running model" />;
  const p = data.prediction;
  const i = p.horizons_years.indexOf(p.primary_horizon);
  const rows = p.horizons_years.map((h, j) => ({ h, risk: p.risk[j], band: [p.lower[j], p.upper[j]] }));
  return (
    <>
      <h1>Personalised risk prediction <span className="pid">{patientId}</span></h1>
      <div className="headline">
        <div className="big">
          <div className="muted small">Estimated {p.primary_horizon}-year cumulative risk</div>
          <div className={`big-num band-${riskBand(p.risk[i])}`}>{pct(p.risk[i])}</div>
          <div className="small">Member spread {pct(p.lower[i])} – {pct(p.upper[i])}</div>
        </div>
        <dl className="kv">
          <dt>Model</dt><dd>{p.model_name}</dd>
          <dt>Uncertainty</dt><dd>{p.uncertainty_method} (n = {p.n_members})</dd>
          <dt>Outcome</dt><dd>Synthetic cardiometabolic event within k years of the last visit</dd>
        </dl>
      </div>
      <section className="card">
        <h3>Future risk trajectory</h3>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis dataKey="h" label={{ value: "Years after index visit", position: "insideBottom", offset: -4 }} />
            <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} domain={[0, (max: number) => Math.min(1, Math.ceil(max * 10) / 10 + 0.05)]} />
            <Tooltip formatter={(v: number | number[]) => (Array.isArray(v) ? `${pct(v[0])} – ${pct(v[1])}` : pct(v))} />
            <Legend verticalAlign="top" height={30} />
            <Area name="Member spread (5th–95th pct)" dataKey="band" stroke="none" fill="var(--band)" isAnimationActive={false} />
            <Line name="Ensemble estimate" dataKey="risk" stroke="var(--ink)" strokeWidth={2.5} dot={{ r: 4 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="muted small">The shaded band shows disagreement between model members. It is not a confidence interval for this
          person's true risk and does not account for distribution shift.</p>
      </section>
      <DisclaimerBanner compact />
      <ExplanationPanel narrative={data.explanation} />
    </>
  );
}
