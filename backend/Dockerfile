# PATIENT-XAI backend: FastAPI + trained models. Research demonstrator, synthetic data only.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/ml:/app/backend \
    PATIENTXAI_ARTIFACTS=/app/artifacts PATIENTXAI_DATA=/app/data/generated
WORKDIR /app

COPY requirements.txt .
# CPU-only PyTorch keeps the image small (~1 GB smaller than the default CUDA wheel).
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
 && pip install -r requirements.txt

COPY ml ml
COPY backend backend
COPY scripts scripts

# Train at build time so `docker compose up` serves immediately and every container
# from this image serves identical, reproducible artifacts. Use --build-arg
# PIPELINE_ARGS=--fast for a ~30 s smoke build.
ARG PIPELINE_ARGS=""
RUN python -m scripts.run_pipeline ${PIPELINE_ARGS} && python -m scripts.write_results > /dev/null || true \
 && python -m scripts.check_artifacts

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"
CMD ["sh", "-c", "python -m scripts.check_artifacts || python -m scripts.run_pipeline; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
