.PHONY: install test lint run up deploy down

install:   ## Create venv and install deps
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

lint:      ## Ruff + mypy
	.venv/bin/ruff check app tests && .venv/bin/mypy app

test:      ## Unit tests
	.venv/bin/pytest -q

run:       ## Run API locally with mock providers
	.venv/bin/uvicorn app.main:app --reload

up:        ## Create local k3d cluster with ingress on :8080
	k3d cluster create document-qa -p "8080:80@loadbalancer"

deploy:    ## Install charts into the local cluster
	@echo "TODO: helm upgrade --install (stage 5)"

down:      ## Delete local cluster
	k3d cluster delete document-qa
