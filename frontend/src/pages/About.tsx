import { api } from "../lib/api";
import { useAsync } from "../lib/context";
import { num, signedPts } from "../lib/format";
import { ErrorBox, Loading } from "../components/Status";

const ROWS: [string, string, string][] = [
  ["Personalised health modelling", "Patient-specific 1–5-year risk trajectory from that patient's own visit history.",
    "Individual calibration: is a 20% estimate right for this person, not just on average?"],
  ["Preventive healthcare", "Risk is estimated before any synthetic event, at the last observed visit.",
    "Turning early warning into evidence about which preventive action helps whom."],
  ["Longitudinal ML", "GRU over irregular visits with explicit time gaps and missingness masks.",
    "Informative missingness, irregular sampling, continuous-time models, temporal leakage."],
  ["Multimodal AI", "A synthetic imaging embedding is fused with tabular sequences; an ablation measures its value.",
    "Real image encoders, cross-modal alignment, missing modalities at inference."],
  ["Counterfactual reasoning", "Model-based what-if simulation, audited against simulator ground truth.",
    "Identifiability: when can P(Y | do(A)) be estimated from observational records, and with what assumptions?"],
  ["Digital twins", "The latent state zₜ and its forward simulation are a minimal 'twin'.",
    "Twin fidelity: updating with new data, validating simulated trajectories, knowing when the twin is wrong."],
  ["Trustworthy AI", "Uncertainty, attribution checks, subgroup metrics, model cards, disclaimers, audit log.",
    "Uncertainty that covers shift, fair performance across groups, explanations that are faithful and useful."],
];

function Findings() {
  const { data, error } = useAsync(() => api.performance(), []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;
  const h = String(data.performance.primary_horizon);
  const m = data.performance.models;
  const auc = (k: string) => m[k].by_horizon[h];
  const ci = (k: string) => `${num(auc(k).auroc, 3)} (95% CI ${num(auc(k).auroc_ci[0], 3)}–${num(auc(k).auroc_ci[1], 3)})`;
  const iv = data.counterfactual_audit.interventions as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  const markers = Object.entries(iv).filter(([, v]) => !v.causal_in_simulator);
  const wrongSign = Object.entries(iv).filter(([, v]) => v.causal_in_simulator && Math.abs(v.true_mean_change) > 0.002
    && Math.sign(v.gru_mean_change) !== Math.sign(v.true_mean_change));
  return (
    <ul>
      <li>{h}-year AUROC on the temporally held-out cohort: GRU ensemble {ci("gru")}; logistic baseline {ci("baseline")};
        GRU without imaging {ci("gru_no_imaging")}. Overlapping intervals mean no model is shown to be better.</li>
      {markers.map(([k, v]) => (
        <li key={k}>“{k}”: true effect {signedPts(v.true_mean_change)} (a marker, not a cause, in the simulator), but the
          GRU simulated {signedPts(v.gru_mean_change)} and the baseline {signedPts(v.baseline_mean_change)}.</li>
      ))}
      {wrongSign.map(([k, v]) => (
        <li key={k}>“{k}”: true effect {signedPts(v.true_mean_change)}, GRU simulation {signedPts(v.gru_mean_change)} —
          the wrong direction, consistent with confounding by indication.</li>
      ))}
    </ul>
  );
}

export function About() {
  return (
    <article className="prose">
      <h1>About the research</h1>
      <p className="lede">This is a <strong>pre-application research demonstrator</strong>. It shows technical preparation
        and, more importantly, it makes the open problems concrete. Its limitations are the motivation for the proposed
        PhD, not something the PhD has already solved.</p>
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>Theme</th><th>What the demonstrator does</th><th>What remains a research problem</th></tr></thead>
          <tbody>{ROWS.map(([a, b, c]) => <tr key={a}><th scope="row">{a}</th><td>{b}</td><td>{c}</td></tr>)}</tbody>
        </table>
      </div>
      <h2>What this demonstrator found (computed live from the current run)</h2>
      <Findings />
      <p>These are the kinds of failure a personalised digital-twin approach must detect and address before any clinical use.</p>
      <h2>Author</h2>
      <p>Built by Olanrewaju (Lanre) Adams Agunloye as preparation for doctoral research in Artificial Medical
        Intelligence. Code is MIT-licensed. Written with AI assistance (disclosed in the repository README).</p>
    </article>
  );
}
