import type { Narrative } from "../lib/api";

const ORDER: { key: keyof Narrative["plain_language"]; title: string; hint: string }[] = [
  { key: "prediction", title: "Prediction", hint: "What the model estimated" },
  { key: "association", title: "Association", hint: "What the estimate moved with" },
  { key: "uncertainty", title: "Uncertainty", hint: "How much model versions disagree" },
  { key: "counterfactual", title: "Counterfactual simulation", hint: "A what-if run through the model" },
  { key: "causality", title: "Causality", hint: "What this does not show" },
];

export function ExplanationPanel({ narrative }: { narrative: Narrative }) {
  const pl = narrative.plain_language;
  return (
    <section className="explain-grid" aria-label="Explanation Engine output">
      <div className="card">
        <h3>Plain-language explanation</h3>
        <p className="muted small">Generated automatically after every prediction. Template-based, no language model.</p>
        {ORDER.filter((o) => pl[o.key]).map((o) => (
          <div key={o.key} className={`concept concept-${o.key}`}>
            <div className="concept-head"><strong>{o.title}</strong><span className="muted small">{o.hint}</span></div>
            <p>{pl[o.key]}</p>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Technical explanation</h3>
        <ul className="tech-list">{narrative.technical.map((t, i) => <li key={i}>{t}</li>)}</ul>
      </div>
    </section>
  );
}
