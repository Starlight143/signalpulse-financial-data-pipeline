# =============================================================================
# SignalPulse Financial Data Pipeline - Makefile
# =============================================================================

.PHONY: help install dev test test-unit test-integration test-fail-closed coverage \
        lint format typecheck build run dev-server clean \
        docker-up docker-down docker-logs docker-build \
        migrate migrate-create seed init-db shell quickstart

# Default target
help:
	@echo "SignalPulse Financial Data Pipeline"
	@echo "====================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install production dependencies"
	@echo "  dev          Install development dependencies"
	@echo "  test         Run all tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-fail-closed Run fail-closed tests only"
	@echo "  coverage     Run tests with coverage report"
	@echo "  lint         Run linter (ruff)"
	@echo "  format       Format code (ruff)"
	@echo "  typecheck    Run type checker (mypy)"
	@echo "  build        Build the package"
	@echo "  run          Run the API server locally"
	@echo "  clean        Clean up generated files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up    Start all services"
	@echo "  docker-down  Stop all services and remove volumes"
	@echo "  docker-logs  Follow docker logs"
	@echo "  docker-build Build docker images"
	@echo ""
	@echo "Database:"
	@echo "  migrate      Run database migrations"
	@echo "  migrate-create Create a new migration"
	@echo "  seed         Seed database with demo data"
	@echo "  init-db      Initialize database (create + migrate + seed)"
	@echo ""
	@echo "Development:"
	@echo "  dev-server   Run development server with auto-reload"
	@echo "  shell        Open Python shell with models imported"

# Installation
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-fail-closed:
	pytest tests/fail_closed/ -v -m fail_closed

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

# Code quality
lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

# Build
build:
	pip install build
	python -m build

# Run
run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

dev-server:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage coverage.xml

# Docker (requires Docker Compose v2 — ships with Docker Desktop 3.x+)
docker-up:
	docker compose up -d

docker-down:
	docker compose down -v

docker-logs:
	docker compose logs -f

docker-build:
	docker compose build

# Database
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

seed:
	python scripts/seed_demo.py

init-db:
	python scripts/init_db.py

# Shell
shell:
	python -i -c "from src.models import *; print('Shell ready. Models imported.')"

# Quick start — waits for all healthchecks before running migrations
quickstart:
	docker compose up -d --wait
	$(MAKE) migrate
	$(MAKE) seed
	@echo ""
	@echo "======================================"
	@echo "SignalPulse Financial Pipeline is ready!"
	@echo "API:  http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "======================================"
