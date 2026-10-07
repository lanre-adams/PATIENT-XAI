import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { api } from "../lib/api";
import { useAsync } from "../lib/context";
import { num, signedPts } from "../lib/format";
import { ErrorBox, Loading } from "../components/Status";

/* eslint-disable @typescript-eslint/no-explicit-any */
const KEYS = ["baseline", "gru", "gru_no_imaging"] as const;

export function Performance() {
  const { data, error } = useAsync(() => api.performance(), []);
  const [calModel, setCalModel] = useState<string>("gru");
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;
  const perf = data.performance;
  const h = String(perf.primary_horizon);
  const m = (k: string) => perf.models[k].by_horizon[h];
  const horizons = Object.keys(perf.models.gru.by_horizon);
  const aucRows = horizons.map((hh) => ({ h: Number(hh), ...Object.fromEntries(KEYS.map((k) => [k, perf.models[k].by_horizon[hh]?.auroc])) }));
  const bins = m(calModel).calibration_bins.map((b: any) => ({ x: b.mean_predicted, y: b.observed_rate, n: b.n }));
  const c = m(calModel).confusion;
  const audit = data.counterfactual_audit;
  return (
    <>
      <h1>Model performance</h1>
      <p className="muted">All numbers below are computed by the training pipeline on the synthetic, temporally held-out test cohort.
        They describe behaviour on simulated data only.</p>
      <section className="card">
        <h3>Evaluation cohort</h3>
        <div className="table-wrap"><table className="data compact">
          <thead><tr><th>Split</th><th>Enrolment years</th><th>Patients</th><th>Observed events</th><th>Known status at {h} y</th></tr></thead>
          <tbody>{Object.entries(perf.cohort).map(([k, v]: [string, any]) => (
            <tr key={k}><td>{k}</td><td>{v.enrolment_years.join(", ")}</td><td>{v.patients}</td><td>{v.events_observed}</td><td>{v.known_status_at_primary_horizon}</td></tr>))}</tbody>
        </table></div>
      </section>
      <section className="card">
        <h3>Discrimination and calibration at {h} years (test cohort)</h3>
        <div className="table-wrap"><table className="data compact">
          <thead><tr><th>Model</th><th>AUROC (95% CI)</th><th>AUPRC (95% CI)</th><th>Brier (95% CI)</th><th>ECE</th><th>Cal. slope</th><th>Cal. intercept</th><th>Sens.</th><th>Spec.</th><th>Threshold</th></tr></thead>
          <tbody>{KEYS.map((k) => { const r = m(k); return (
            <tr key={k}><td>{perf.models[k].name}</td>
              <td>{num(r.auroc, 3)} ({num(r.auroc_ci[0], 3)}–{num(r.auroc_ci[1], 3)})</td>
              <td>{num(r.auprc, 3)} ({num(r.auprc_ci[0], 3)}–{num(r.auprc_ci[1], 3)})</td>
              <td>{num(r.brier, 3)} ({num(r.brier_ci[0], 3)}–{num(r.brier_ci[1], 3)})</td>
              <td>{num(r.ece, 3)}</td><td>{num(r.calibration_slope)}</td><td>{num(r.calibration_intercept)}</td>
              <td>{num(r.sensitivity)}</td><td>{num(r.specificity)}</td><td>{num(r.threshold, 3)}</td></tr>); })}</tbody>
        </table></div>
        <p className="small muted">Bootstrap 95% CIs (patient resampling). Threshold chosen by Youden's index on the 2020 validation cohort, then applied unchanged to the test cohort. n = {m("gru").n} with known 3-year status; prevalence {num(m("gru").prevalence, 3)}.</p>
      </section>
      <div className="two-col">
        <section className="card">
          <div className="card-head"><h3>Calibration</h3>
            <select value={calModel} onChange={(e) => setCalModel(e.target.value)} aria-label="Calibration model">
              {KEYS.map((k) => <option key={k} value={k}>{perf.models[k].name}</option>)}</select></div>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: 8 }}>
              <CartesianGrid stroke="var(--grid)" />
              <XAxis type="number" dataKey="x" domain={[0, 0.8]} name="Mean predicted" tickFormatter={(v) => v.toFixed(1)} label={{ value: "Mean predicted risk (decile)", position: "insideBottom", offset: -8 }} />
              <YAxis type="number" dataKey="y" domain={[0, 0.8]} name="Observed" tickFormatter={(v) => v.toFixed(1)} />
              <ZAxis dataKey="n" range={[40, 40]} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Scatter data={[{ x: 0, y: 0 }, { x: 0.8, y: 0.8 }]} line={{ stroke: "var(--muted)", strokeDasharray: "4 4" }} shape={() => <g />} isAnimationActive={false} />
              <Scatter name="Deciles" data={bins} fill="var(--ink)" isAnimationActive={false} />
            </ScatterChart>
          </ResponsiveContainer>
          <p className="small muted">Points on the dashed diagonal are perfectly calibrated deciles.</p>
        </section>
        <section className="card">
          <h3>Confusion matrix at threshold</h3>
          <table className="confusion" aria-label="Confusion matrix">
            <thead><tr><th /><th>Predicted high</th><th>Predicted low</th></tr></thead>
            <tbody><tr><th>Event by {h} y</th><td className="tp">{c.tp}</td><td>{c.fn}</td></tr>
              <tr><th>No event</th><td>{c.fp}</td><td className="tn">{c.tn}</td></tr></tbody>
          </table>
          <p className="small muted">{perf.models[calModel].name}. PPV {num(m(calModel).ppv)}, NPV {num(m(calModel).npv)}.</p>
          <h3>AUROC by horizon</h3>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={aucRows}><CartesianGrid stroke="var(--grid)" /><XAxis dataKey="h" /><YAxis domain={[0.5, 1]} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} /><Legend verticalAlign="top" height={30} />
              <Line dataKey="baseline" name="Baseline" stroke="var(--muted)" isAnimationActive={false} />
              <Line dataKey="gru" name="GRU" stroke="var(--ink)" isAnimationActive={false} />
              <Line dataKey="gru_no_imaging" name="GRU − imaging" stroke="var(--accent)" strokeDasharray="4 3" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </div>
      <section className="card">
        <h3>Subgroup check (sex) at {h} years</h3>
        <div className="table-wrap"><table className="data compact">
          <thead><tr><th>Model</th><th>Group</th><th>n</th><th>Observed rate</th><th>Mean predicted</th><th>AUROC</th><th>Sens.</th><th>Spec.</th></tr></thead>
          <tbody>{KEYS.flatMap((k) => Object.entries(perf.models[k].subgroups_sex).map(([g, r]: [string, any]) => (
            <tr key={k + g}><td>{perf.models[k].name}</td><td>{g === "F" ? "Female" : "Male"}</td><td>{r.n}</td><td>{num(r.prevalence, 3)}</td><td>{num(r.mean_predicted, 3)}</td><td>{num(r.auroc, 3)}</td><td>{num(r.sensitivity)}</td><td>{num(r.specificity)}</td></tr>)))}</tbody>
        </table></div>
        <p className="small muted">Small subgroups give wide uncertainty; a single sex split is a minimum check, not a fairness audit.</p>
      </section>
      <section className="card">
        <h3>Counterfactual audit: model simulation vs simulator ground truth ({audit.horizon_years}-year risk)</h3>
        <div className="table-wrap"><table className="data compact">
          <thead><tr><th>Intervention</th><th>n</th><th>Causal in simulator?</th><th>True mean change</th><th>GRU simulated</th><th>Baseline simulated</th><th>GRU–truth correlation</th><th>Sign agreement</th></tr></thead>
          <tbody>{Object.entries(audit.interventions).map(([k, v]: [string, any]) => (
            <tr key={k}><td>{k}</td><td>{v.n}</td><td>{v.causal_in_simulator ? "yes" : "no (marker)"}</td>
              <td>{signedPts(v.true_mean_change)}</td><td>{signedPts(v.gru_mean_change)}</td><td>{signedPts(v.baseline_mean_change)}</td>
              <td>{v.gru_corr_with_truth == null ? "n/a" : num(v.gru_corr_with_truth)}</td>
              <td>{v.gru_sign_agreement == null ? "n/a" : `${Math.round(100 * v.gru_sign_agreement)}%`}</td></tr>))}</tbody>
        </table></div>
        <p className="small">Read this table as the central result of the demonstrator: good discrimination does not make model-based
          what-if simulations causally valid. Ground truth exists here only because the data are simulated.</p>
      </section>
      <section className="card">
        <h3>Limitations</h3>
        <ul className="small">
          <li>Synthetic simulator written by the author; real cohorts are messier and less separable.</li>
          <li>Complete-case evaluation per horizon (no IPCW); one temporal split; no external dataset.</li>
          <li>A 7-member ensemble and 30 bootstrap refits only approximate epistemic uncertainty.</li>
        </ul>
      </section>
    </>
  );
}
