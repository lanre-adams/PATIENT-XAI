# PATIENT-XAI developer commands. Research demonstrator — synthetic data only.
PY ?= python3
export PYTHONPATH := ml:backend:.

.PHONY: help install pipeline pipeline-fast results seed api web test test-unit test-integration test-model test-frontend lint docker-build docker-up clean

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

install:         ## install Python and Node dependencies
	$(PY) -m pip install -r requirements-dev.txt
	cd frontend && npm ci

pipeline:        ## simulate data, train, evaluate, save artifacts (full config)
	$(PY) -m scripts.run_pipeline && $(PY) -m scripts.write_results > /dev/null

pipeline-fast:   ## small, quick pipeline run
	$(PY) -m scripts.run_pipeline --fast

results:         ## regenerate docs/results.md from artifacts
	$(PY) -m scripts.write_results

seed:            ## reseed the database from data/generated
	$(PY) -m scripts.seed_db

api:             ## run the API on :8000
	$(PY) -m uvicorn app.main:app --reload --port 8000

web:             ## run the frontend dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

test: test-unit test-model test-integration test-frontend  ## everything

test-unit:       ## simulator, features, explanation engine
	$(PY) -m pytest -q tests/test_data_generation.py tests/test_explanation_engine.py

test-model:      ## model behaviour and attribution properties
	$(PY) -m pytest -q -m model

test-integration: ## HTTP API end to end
	$(PY) -m pytest -q -m integration

test-frontend:   ## component and unit tests
	cd frontend && npm test

lint:            ## ruff + TypeScript
	ruff check ml backend scripts tests
	cd frontend && npm run lint

docker-build:    ## validate compose file and build images
	docker compose config --quiet && docker compose build

docker-up:       ## build and run the full stack
	docker compose up --build

clean:
	rm -rf artifacts data/generated data/*.db frontend/dist .pytest_cache
