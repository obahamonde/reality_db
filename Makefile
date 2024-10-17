# Configuration Variables
PORT=8000
APP=realitydb
VERSION=$(shell git describe --tags --always --dirty || echo "latest")
IMAGE_NAME=$(APP):$(VERSION)

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Default target: Show menu when no target is provided
.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk '/^[a-zA-Z_-]+:/ {print "  " $$1}' $(MAKEFILE_LIST) | sed 's/://'
	@echo ""
	@echo "Examples:"
	@echo "  make dev        - Run development tasks (format, lint, test)"
	@echo "  make build      - Build the Docker image"
	@echo "  make test       - Run tests with coverage"
	@echo "  make deploy     - Deploy the service"
	@echo "  make monitor    - Run health checks and metrics monitoring"
	@echo ""

# DEV: Development tasks
.PHONY: dev
dev: install format lint test

.PHONY: format
format:
	poetry run black .
	poetry run isort .

.PHONY: lint
lint:
	poetry run black .
	poetry run isort .
.PHONY: run-dev
run-dev:
	poetry run uvicorn realitydb.rpc_server:app --reload --port $(PORT)

# CODE: Manage dependencies and environments
.PHONY: install
install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install poetry
	poetry install
	poetry export --without-hashes --format=requirements.txt > requirements.txt

.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .venv dist build *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage
	rm -f requirements.txt
	rm -r *.lock

# TEST: Run unit and integration tests
.PHONY: test
test:
	poetry run pytest

# BUILD: Build Docker image for deployment
.PHONY: build
build:
	docker build -t $(IMAGE_NAME) .

.PHONY: compose-up
compose-up:
	docker compose up -d --build

# RELEASE: Tag and push image to a container registry
.PHONY: release
release:
	docker tag $(IMAGE_NAME) your-registry/$(IMAGE_NAME)
	docker push your-registry/$(IMAGE_NAME)

# DEPLOY: Deploy the service (with Docker Compose)
.PHONY: deploy
deploy: compose-down compose-up

.PHONY: compose-down
compose-down:
	docker compose down

.PHONY: deploy-clean
deploy-clean:
	docker compose down --volumes

# OPS: Check logs, running containers, or restart the app
.PHONY: ops
ops: status logs

.PHONY: status
status:
	docker ps | grep $(APP) || echo "Service not running."

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: restart
restart:
	docker compose restart

# MONITOR: Health checks and monitoring tasks
.PHONY: monitor
monitor: health-check metrics

.PHONY: health-check
health-check:
	curl --fail http://localhost:$(PORT)/health || echo "Service is not healthy."

.PHONY: metrics
metrics:
	docker stats --no-stream $(shell docker ps -q --filter "name=$(APP)")
