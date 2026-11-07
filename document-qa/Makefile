.PHONY: install test test-pg db db-stop lint run run-pg up deploy down

install:   ## Create venv and install deps
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

lint:      ## Ruff + mypy
	.venv/bin/ruff check app tests && .venv/bin/mypy app

test:      ## Unit tests
	.venv/bin/pytest -q

test-pg:   ## Unit tests incl. Postgres backend (needs `make db`)
	TEST_DATABASE_URL=postgresql://qa:qa@localhost:5432/qa .venv/bin/pytest -q

db:        ## Local Postgres with pgvector on :5432
	docker run -d --rm --name qa-db -p 5432:5432 \
	  -e POSTGRES_USER=qa -e POSTGRES_PASSWORD=qa -e POSTGRES_DB=qa pgvector/pgvector:pg16

db-stop:   ## Stop local Postgres
	docker stop qa-db

run-pg:    ## Run API locally against local Postgres
	STORE_BACKEND=postgres .venv/bin/uvicorn app.main:app --reload

run:       ## Run API locally with mock providers
	.venv/bin/uvicorn app.main:app --reload

up:        ## Create local k3d cluster with ingress on :8080
	k3d cluster create document-qa -p "8080:80@loadbalancer"

deploy:    ## Install charts into the local cluster
	@echo "TODO: helm upgrade --install (stage 5)"

down:      ## Delete local cluster
	k3d cluster delete document-qa
