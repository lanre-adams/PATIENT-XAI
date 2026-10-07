# Methodology notes

**Outcome definition.** Discrete annual hazards h_y for y = 1..5 after the index (last observed) visit;
cumulative risk R_k = 1 − ∏_{y≤k}(1 − h_y). Both models share this head, so trajectories are monotone by construction.

**Censoring.** Training uses the discrete-time likelihood: an event in year e contributes years 1..e;
a censored patient contributes only fully observed years. Evaluation at horizon k is complete-case
(known status at k). IPCW is future work.

**Leakage controls.** Standardisation statistics fitted on the training cohort only; temporal split by enrolment
year; threshold and early stopping use the 2020 validation cohort only; the outcome and simulator truth are never
model inputs; the simulator truth table is used solely by the counterfactual audit.

**Uncertainty.** Ensemble/bootstrap 5th–95th percentile of member predictions. Counterfactual differences are
paired within member (member m with and without the edit), so the interval reflects model disagreement about
the *difference*, not two independent intervals.

**Attribution.** Baseline: exact w_j·x_j on hazard log-odds (standardised features, training-mean reference).
GRU: integrated gradients on the ensemble-mean R_k, 32-step Riemann approximation, all-zero standardised
baseline (training-mean continuous values, no treatment, nothing measured). Completeness gap is reported.

**Counterfactual audit.** For 150 sampled test patients, apply each intervention to the index visit, compute
the model-based change in 3-year risk, and compare with the simulator's do-intervention change computed from the
known structural hazard (latent state, frailty and drift held at their true values).

**Similarity.** Cosine similarity of GRU member-0 latent state z_t against the training cohort.
