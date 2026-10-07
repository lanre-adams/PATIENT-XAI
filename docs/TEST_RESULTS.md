# Test results (actual output)

Recorded 2026-10-07 in a Linux sandbox (Python 3.13.16, PyTorch 2.14.1, Node 22.22.0, 2 vCPU). Re-run with `make test`.

## Python — `python -m pytest -v` (38 tests: unit, model, integration) + reproducibility test
```
tests/test_api.py::test_health PASSED                                    [  2%]
tests/test_api.py::test_meta_has_disclaimer_and_modifiables PASSED       [  5%]
tests/test_api.py::test_patient_list_and_detail PASSED                   [  7%]
tests/test_api.py::test_unknown_patient_404 PASSED                       [ 10%]
tests/test_api.py::test_predict[gru] PASSED                              [ 13%]
tests/test_api.py::test_predict[baseline] PASSED                         [ 15%]
tests/test_api.py::test_invalid_model_rejected PASSED                    [ 18%]
tests/test_api.py::test_explain_endpoint PASSED                          [ 21%]
tests/test_api.py::test_counterfactual_endpoint PASSED                   [ 23%]
tests/test_api.py::test_counterfactual_validation[changes0] PASSED       [ 26%]
tests/test_api.py::test_counterfactual_validation[changes1] PASSED       [ 28%]
tests/test_api.py::test_counterfactual_validation[changes2] PASSED       [ 31%]
tests/test_api.py::test_counterfactual_validation[changes3] PASSED       [ 34%]
tests/test_api.py::test_counterfactual_rejects_malformed_id PASSED       [ 36%]
tests/test_api.py::test_similar PASSED                                   [ 39%]
tests/test_api.py::test_performance PASSED                               [ 42%]
tests/test_api.py::test_report_generation[html-text/html] PASSED         [ 44%]
tests/test_api.py::test_report_generation[pdf-application/pdf] PASSED    [ 47%]
tests/test_api.py::test_report_generation[json-application/json] PASSED  [ 50%]
tests/test_api.py::test_requests_are_logged PASSED                       [ 52%]
tests/test_data_generation.py::test_simulator_is_deterministic PASSED    [ 55%]
tests/test_data_generation.py::test_cohort_is_longitudinal_and_synthetic PASSED [ 57%]
tests/test_data_generation.py::test_outcomes_and_labels_are_consistent PASSED [ 60%]
tests/test_data_generation.py::test_true_risk_curve_monotone_and_causal_structure PASSED [ 63%]
tests/test_data_generation.py::test_temporal_split PASSED                [ 65%]
tests/test_explanation_engine.py::test_all_five_concepts_present PASSED  [ 68%]
tests/test_explanation_engine.py::test_no_medical_advice PASSED          [ 71%]
tests/test_explanation_engine.py::test_technical_includes_calibration_caveat PASSED [ 73%]
tests/test_models.py::test_survival_targets_respect_censoring PASSED     [ 76%]
tests/test_models.py::test_person_period_expansion PASSED                [ 78%]
tests/test_models.py::test_prediction_is_valid_monotone_risk_with_interval[gru] PASSED [ 81%]
tests/test_models.py::test_prediction_is_valid_monotone_risk_with_interval[baseline] PASSED [ 84%]
tests/test_models.py::test_integrated_gradients_completeness PASSED      [ 86%]
tests/test_models.py::test_baseline_attribution_is_exact_on_logit_scale PASSED [ 89%]
tests/test_models.py::test_counterfactual_identity_and_direction PASSED  [ 92%]
tests/test_models.py::test_counterfactual_does_not_mutate_inputs PASSED  [ 94%]
tests/test_models.py::test_feature_space_roundtrip PASSED                [ 97%]
tests/test_models.py::test_metrics_are_computed_not_hardcoded PASSED     [100%]
================== 38 passed, 1 warning in 157.22s (0:02:37) ===================
```

Reproducibility test, run separately afterwards:
```
tests/test_reproducibility.py::test_pipeline_is_reproducible PASSED
1 passed in 310.20s
```
Total Python tests: **39 passed, 0 failed**.

## Lint — `ruff check ml backend scripts tests`
```
All checks passed!
```

## Frontend — `npm run lint` (tsc --noEmit): exit 0, no errors

## Frontend — `npx vitest run`
```
 ✓ src/__tests__/components.test.tsx (4 tests) 100ms
 ✓ src/__tests__/format.test.ts (3 tests) 3ms
 Test Files  2 passed (2)
      Tests  7 passed (7)
```

## Frontend — `npm run build`
```
dist/index.html                   0.80 kB │ gzip:   0.47 kB
dist/assets/index-DjPKqmrN.css    8.07 kB │ gzip:   2.34 kB
dist/assets/index-3Thms6-g.js   617.02 kB │ gzip: 177.06 kB
✓ built in 13.19s
```

## Full pipeline — `python -m scripts.run_pipeline`
Completed in 250.8 s on 2 vCPU; outputs in `docs/results.md`. Re-running with the same seed reproduced identical metrics.

## End-to-end smoke test
API (uvicorn) + built frontend (vite preview) run together; all eight pages exercised with Playwright/Chromium; screenshots in `docs/screenshots/`.

## Docker
- `docker compose config --quiet`: **valid**.
- `docker compose build` / `docker compose up --build`: **NOT EXECUTED IN THIS ENVIRONMENT** — the sandbox could not pull base images (Docker Hub and mirrors returned 403). Every step the containers run (pip install, pipeline, uvicorn, `npm ci`, `npm run build`) was executed natively above. Run `make docker-build` on your machine and record the result here.
