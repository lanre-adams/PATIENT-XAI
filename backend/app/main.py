"""PATIENT-XAI API. Research demonstrator — not a medical device."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field, field_validator

from patientxai import DISCLAIMER, __version__
from patientxai.config import HORIZONS, MODIFIABLE, PRIMARY_HORIZON

from .service import NotFound, Service

ModelKey = Literal["gru", "baseline"]


def validate_changes(v: dict[str, float]) -> dict[str, float]:
    for k, val in v.items():
        if k not in MODIFIABLE:
            raise ValueError(f"'{k}' is not a modifiable variable; allowed: {sorted(MODIFIABLE)}")
        lim = MODIFIABLE[k]
        if not lim["min"] <= val <= lim["max"]:
            raise ValueError(f"{k}={val} outside allowed range [{lim['min']}, {lim['max']}]")
        if k == "smoking_current" and val not in (0, 1):
            raise ValueError("smoking_current must be 0 or 1")
    return v


class CounterfactualRequest(BaseModel):
    patient_id: str = Field(pattern=r"^SYN-\d{5}$")
    model: ModelKey = "gru"
    changes: dict[str, float] = Field(min_length=1)

    @field_validator("changes")
    @classmethod
    def _check(cls, v: dict[str, float]):
        return validate_changes(v)


class ReportRequest(BaseModel):
    patient_id: str = Field(pattern=r"^SYN-\d{5}$")
    model: ModelKey = "gru"
    format: Literal["html", "pdf", "json"] = "html"
    changes: dict[str, float] | None = None

    @field_validator("changes")
    @classmethod
    def _check(cls, v):
        return None if not v else validate_changes(v)


def create_app(service: Service | None = None) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["svc"] = service or Service()
        yield

    app = FastAPI(title="PATIENT-XAI API", version=__version__, lifespan=lifespan,
                  description=f"**{DISCLAIMER}** Personalised longitudinal risk, attribution, uncertainty "
                              "and counterfactual simulation on synthetic data.")
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    def svc() -> Service:
        return state["svc"]

    @app.exception_handler(NotFound)
    async def _nf(_: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": f"Synthetic patient {exc} not found"})

    @app.middleware("http")
    async def _disclaimer_header(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Research-Demonstrator"] = "not-a-medical-device; synthetic-data-only"
        return resp

    @app.get("/api/health")
    def health():
        s = state.get("svc")
        return {"status": "ok" if s else "starting", "version": __version__,
                "models_loaded": bool(s), "disclaimer": DISCLAIMER}

    @app.get("/api/meta")
    def meta():
        return svc().meta()

    @app.get("/api/patients")
    def patients(split: Literal["train", "val", "test"] | None = None, q: str | None = Query(None, max_length=12),
                 limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
        return svc().list_patients(split, q, limit, offset)

    @app.get("/api/patients/{pid}")
    def patient(pid: str):
        return svc().patient_detail(pid)

    @app.get("/api/predict/{pid}")
    def predict(pid: str, model: ModelKey = "gru"):
        return svc().predict(pid, model)

    @app.get("/api/explain/{pid}")
    def explain(pid: str, model: ModelKey = "gru", horizon: int = PRIMARY_HORIZON):
        if horizon not in HORIZONS:
            raise HTTPException(422, f"horizon must be one of {HORIZONS}")
        return svc().explain(pid, model, horizon)

    @app.post("/api/counterfactual")
    def counterfactual(req: CounterfactualRequest):
        return svc().counterfactual(req.patient_id, req.model, req.changes)

    @app.get("/api/similar/{pid}")
    def similar(pid: str, k: int = Query(10, ge=1, le=50)):
        return svc().similar(pid, k)

    @app.get("/api/performance")
    def performance():
        return svc().performance_report()

    @app.post("/api/report")
    def report(req: ReportRequest):
        out = svc().report(req.patient_id, req.model, req.changes, req.format)
        name = f"patient-xai-report-{req.patient_id}"
        if req.format == "html":
            return HTMLResponse(out, headers={"Content-Disposition": f'attachment; filename="{name}.html"'})
        if req.format == "pdf":
            return Response(out, media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})
        return out

    return app


app = create_app()
