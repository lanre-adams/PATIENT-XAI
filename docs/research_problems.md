# Open research problems exposed by the demonstrator

Each item names what the MVP does, why it is insufficient, and what doctoral work would address.

| # | Problem | What the MVP does | Why it is not enough |
|---|---|---|---|
| 1 | Heterogeneous longitudinal sampling | Δt as an input feature to a GRU | Visit timing is itself informative (sicker people are seen more often); continuous-time models (neural ODE/CDE, temporal point processes) and informative-observation modelling are needed |
| 2 | Missingness | LOCF + observation masks | LOCF can leak stale values as if current; MNAR missingness biases both prediction and counterfactuals |
| 3 | Multimodal alignment | Synthetic 8-d imaging vector, LOCF'd | Real images arrive at different times and resolutions from labs; modality-missing-at-inference and cross-modal alignment are unsolved here; the ablation shows no gain |
| 4 | Individualised calibration | Cohort calibration curve, ECE, slope | A well-calibrated cohort can be miscalibrated for individuals and subgroups; "individual calibration" is not identifiable without further assumptions |
| 5 | Distribution shift | One temporal split with built-in cohort drift | No shift detection, no shift-aware uncertainty, no external site |
| 6 | Uncertainty | 7-member ensemble / 30 bootstraps | Ignores aleatoric, label and shift uncertainty; no coverage guarantee (conformal / survival conformal methods are candidates) |
| 7 | Causal identifiability | None — model-based edits only | The audit shows marker variables and confounded treatments produce wrong-magnitude and wrong-sign "effects"; needs target-trial emulation, g-methods, or causal digital twins with stated assumptions |
| 8 | Counterfactual validity | Edits the index visit only | A real intervention changes the future trajectory (and other variables downstream); needs a generative dynamic model and time-varying treatment methods |
| 9 | Fairness | Sex subgroup table | No intersectional analysis, no socioeconomic or ethnicity variables, no fairness-calibration trade-off study |
| 10 | Robustness | None | No perturbation, adversarial or corrupted-input tests for health records |
| 11 | Clinical validation | None | Requires clinical partners, real cohorts, prospective or silent-deployment evaluation |
| 12 | External validation | None | Transportability across hospitals/countries (e.g. UK vs Nigerian programme data) |
| 13 | Privacy | Synthetic data, no auth | Real work needs TREs, federated or privacy-preserving learning, disclosure control on explanations |
| 14 | Digital-twin fidelity | Latent z_t + forward hazard | No updating as new data arrive, no validation of simulated trajectories against what later happens |
