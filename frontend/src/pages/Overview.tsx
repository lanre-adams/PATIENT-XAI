export function Overview() {
  return (
    <article className="prose">
      <h1>Research overview</h1>
      <p className="lede">
        PATIENT-XAI is a small, honest test-bed for one question: <em>when a longitudinal model produces a personalised
        risk trajectory, an explanation and a “what-if” simulation, which parts of that output can be trusted, and
        which cannot?</em> It runs entirely on a synthetic cohort whose data-generating process is known, so every
        claim the models make can be checked against ground truth.
      </p>

      <h2>Research question</h2>
      <p>Can a personalised latent-state model of irregular, partially missing, multimodal health records produce
        risk trajectories that are well-calibrated, explainable and uncertainty-aware — and under what conditions do
        its counterfactual simulations agree with true interventional effects?</p>

      <h2>Working hypotheses</h2>
      <ol>
        <li><strong>H1.</strong> A sequence model that sees visit timing and missingness explicitly matches a transparent
          survival baseline on discrimination and calibration under temporal shift. (Result: see Model performance.)</li>
        <li><strong>H2.</strong> Model-based counterfactuals diverge from true interventional effects when variables are
          markers rather than causes, or when treatment is confounded by indication. (Result: see the counterfactual audit.)</li>
        <li><strong>H3.</strong> Ensemble disagreement is informative but insufficient as a sole uncertainty statement.</li>
      </ol>

      <h2>Methodology</h2>
      <ul>
        <li><strong>Data.</strong> 3,000 synthetic patients, 3–13 irregular visits each, vital signs, labs with
          intermittent missingness, synthetic medication status, and an 8-dimensional synthetic imaging embedding.
          Outcome: a synthetic cardiometabolic event within 1–5 years of the last visit, with right-censoring.</li>
        <li><strong>Validation.</strong> Temporal split by enrolment year (train 2015–19, validate 2020, test 2021–22),
          with cohort drift built in.</li>
        <li><strong>Models.</strong> Discrete-time survival logistic regression (transparent baseline) and a GRU
          deep ensemble with a discrete-time survival head.</li>
        <li><strong>Trust layer.</strong> Bootstrap / ensemble uncertainty, exact linear attribution and integrated
          gradients with a completeness check, counterfactual simulation, latent-space neighbours, and a template-based
          Explanation Engine.</li>
      </ul>

      <h2>Architecture</h2>
      <figure className="arch" aria-label="Architecture diagram">
        <div className="arch-row">
          <div className="arch-box">Longitudinal visits X₁…Xₜ<br /><span>vitals · labs · masks · Δt</span></div>
          <div className="arch-box">Imaging embedding Iₜ<br /><span>synthetic, 8-d (stand-in for an image encoder)</span></div>
          <div className="arch-box">Static context C<br /><span>sex · smoking</span></div>
        </div>
        <div className="arch-arrow">↓</div>
        <div className="arch-row"><div className="arch-box wide">GRU encoder → latent patient state zₜ = f(X₁…Xₜ, Iₜ, C)</div></div>
        <div className="arch-arrow">↓</div>
        <div className="arch-row">
          <div className="arch-box">Hazard head<br /><span>P(event in year k | zₜ), k = 1…5</span></div>
          <div className="arch-box">Uncertainty<br /><span>deep ensemble · bootstrap</span></div>
          <div className="arch-box">Attribution<br /><span>integrated gradients · exact linear</span></div>
          <div className="arch-box">Counterfactual<br /><span>edit index visit, re-run model</span></div>
        </div>
        <figcaption>The demonstrator computes P(Y<sub>t+k</sub> | edited x), not P(Y<sub>t+k</sub> | do(A=a′)). The PhD addresses the gap between them.</figcaption>
      </figure>

      <h2>Limitations</h2>
      <ul>
        <li>Synthetic data from a simulator the author wrote: the results test the pipeline, not medicine.</li>
        <li>No clinical validation, no external validation, no regulatory status of any kind.</li>
        <li>Imaging is represented by synthetic embeddings, not images.</li>
        <li>Counterfactuals edit only the index visit and are not causal estimates.</li>
        <li>Complete-case evaluation per horizon; no censoring weights.</li>
      </ul>

      <h2>Ethics and trustworthiness</h2>
      <ul>
        <li>No real patient data are used or needed; identifiers are synthetic (SYN-#####).</li>
        <li>Every screen carries the research-demonstrator notice; the API adds a response header saying the same.</li>
        <li>The Explanation Engine is template-based and tested to never emit treatment advice.</li>
        <li>Subgroup (sex) metrics are reported alongside cohort metrics.</li>
        <li>All requests that produce predictions or reports are logged with model version for auditability.</li>
      </ul>
    </article>
  );
}
