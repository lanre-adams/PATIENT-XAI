# Architecture

```mermaid
flowchart LR
  subgraph Data["Synthetic data (ml/patientxai/simulate.py)"]
    SIM[Known structural simulator] --> CSV[(CSV: patients, visits, outcomes, simulator_truth)]
  end
  CSV --> SEED[Seed] --> DB[(SQLite via SQLAlchemy<br/>PostgreSQL-ready)]
  subgraph ML["Training pipeline (ml/patientxai/pipeline.py)"]
    FS[FeatureSpace<br/>LOCF + masks + Δt<br/>fit on train only] --> BASE[Discrete-time logistic<br/>+ 30 bootstrap refits]
    FS --> GRU[GRU deep ensemble x7<br/>discrete-time survival head]
    FS --> ABL[GRU without imaging<br/>ablation x3]
    BASE & GRU & ABL --> EVAL[Temporal test evaluation<br/>AUROC/AUPRC/Brier/ECE + bootstrap CIs]
    GRU & BASE --> AUD[Counterfactual audit<br/>vs simulator do-effects]
  end
  CSV --> FS
  EVAL & AUD --> ART[(artifacts/)]
  subgraph API["FastAPI (backend/app)"]
    SVC[Service] --> BUN[ModelBundle<br/>predict · explain · counterfactual · similar]
    SVC --> EE[Explanation Engine<br/>template-based]
    SVC --> REP[Report HTML/PDF/JSON]
  end
  ART --> BUN
  DB --> SVC
  API <-->|/api| UI[React + TypeScript UI<br/>8 research pages]
```

## Future multimodal research architecture (PhD target, not implemented)

```mermaid
flowchart LR
  IMG[Imaging series I_t] --> IE[Image encoder<br/>pretrained CNN/ViT]
  TAB[Irregular visits X_1..X_t] --> TE[Longitudinal encoder<br/>continuous-time / temporal transformer]
  CTX[Static context C] --> FUSE
  IE --> FUSE[Fusion with missing-modality handling]
  TE --> FUSE
  FUSE --> Z[Personalised latent state z_t]
  Z --> P[Risk head<br/>P(Y_t+k given z_t)]
  Z --> U[Uncertainty head<br/>ensembles / conformal / shift-aware]
  Z --> CF[Counterfactual head<br/>P(Y_t+k given do(A=a'), z_t)<br/>only under stated identification assumptions]
  P & U & CF --> EXP[Explanations + individual calibration checks]
```
