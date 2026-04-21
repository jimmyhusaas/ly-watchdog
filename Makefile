.PHONY: help install up down logs migrate revision shell test lint fmt type check clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Create venv + install deps (requires uv)
	uv venv
	uv pip install -e ".[dev]"

up: ## docker compose up (build + run)
	docker compose up --build -d

down: ## docker compose down
	docker compose down

logs: ## Tail app logs
	docker compose logs -f app

migrate: ## Run migrations against the running DB
	docker compose run --rm migrate

revision: ## Create a new alembic revision. usage: make revision m="add votes"
	docker compose run --rm app alembic revision --autogenerate -m "$(m)"

shell: ## Open a psql shell to the running DB
	docker compose exec postgres psql -U watchdog -d ly_watchdog

test: ## Run tests
	uv run pytest

lint: ## Ruff lint
	uv run ruff check .

fmt: ## Ruff format
	uv run ruff format .

type: ## mypy
	uv run mypy app scrapers

check: lint type test ## Lint + type-check + test

clean: ## Remove caches
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
