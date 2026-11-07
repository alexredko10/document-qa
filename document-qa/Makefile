.PHONY: install test test-pg db db-stop lint run run-pg up deploy down

# Local Postgres runs in Docker on DB_PORT (5433 avoids clashing with a host
# Postgres on 5432). Override: make db DB_PORT=5544
DB_PORT ?= 5433
DB_URL      = postgresql://qa:qa@localhost:$(DB_PORT)/qa
TEST_DB_URL = postgresql://qa:qa@localhost:$(DB_PORT)/qa_test

install:   ## Create venv and install deps
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

lint:      ## Ruff + mypy
	.venv/bin/ruff check app tests && .venv/bin/mypy app

test:      ## Unit tests (Postgres cases are skipped)
	.venv/bin/pytest -q

test-pg:   ## Unit tests incl. Postgres backend (needs `make db`); uses its own qa_test database
	TEST_DATABASE_URL=$(TEST_DB_URL) .venv/bin/pytest -q

db:        ## Local Postgres + pgvector on :$(DB_PORT) with databases qa and qa_test
	docker run -d --rm --name qa-db -p $(DB_PORT):5432 \
	  -e POSTGRES_USER=qa -e POSTGRES_PASSWORD=qa -e POSTGRES_DB=qa pgvector/pgvector:pg16
	@until docker exec qa-db pg_isready -U qa -d qa >/dev/null 2>&1; do sleep 1; done
	@docker exec qa-db createdb -U qa qa_test 2>/dev/null || true
	@echo "Postgres ready on localhost:$(DB_PORT) (qa, qa_test)"

db-stop:   ## Stop local Postgres (data is discarded)
	docker stop qa-db

run-pg:    ## Run API locally against local Postgres
	STORE_BACKEND=postgres DATABASE_URL=$(DB_URL) .venv/bin/uvicorn app.main:app --reload

run:       ## Run API locally with mock providers
	.venv/bin/uvicorn app.main:app --reload

up:        ## Create local k3d cluster with ingress on :8080
	k3d cluster create document-qa -p "8080:80@loadbalancer"

deploy:    ## Install charts into the local cluster
	@echo "TODO: helm upgrade --install (stage 5)"

down:      ## Delete local cluster
	k3d cluster delete document-qa