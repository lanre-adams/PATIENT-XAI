# Publishing to GitHub

**Suggested repository name:** `patient-xai`
**Suggested description:** Research demonstrator (synthetic data, not a medical device): personalised longitudinal risk trajectories with uncertainty, explainability and an audit of counterfactual "what-if" simulations against known causal ground truth.
**Topics:** `medical-ai` `longitudinal` `survival-analysis` `explainable-ai` `uncertainty-quantification` `counterfactual` `causal-inference` `digital-twin` `pytorch` `fastapi` `react`

```bash
cd patient-xai
git init
git add .
git commit -m "Initial PATIENT-XAI research demonstrator"
git branch -M main
git remote add origin https://github.com/<your-username>/patient-xai.git
git push -u origin main

# release tag
git tag -a v0.1.0-mvp -m "PATIENT-XAI v0.1.0: synthetic cohort, baseline + GRU ensemble, counterfactual audit"
git push origin v0.1.0-mvp
```

Then on GitHub: Releases → draft a release from `v0.1.0-mvp`, paste the "Evaluation" and "Counterfactual analysis" sections of the README, and attach `docs/results.md`.

Planned tags: `v0.2.0` (IPCW, conformal intervals, real imaging component), `v0.3.0` (g-formula / target-trial-emulation counterfactual baseline).
