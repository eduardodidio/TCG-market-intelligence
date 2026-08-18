.PHONY: setup test lint format clean run-backfill run-update help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv, install deps (dev + prod)
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"

test: ## Run pytest with verbose output
	.venv/bin/python -m pytest tests/ -v

lint: ## Run ruff check
	.venv/bin/ruff check src/ tests/

format: ## Run ruff format
	.venv/bin/ruff format src/ tests/

clean: ## Remove __pycache__, .pytest_cache, *.egg-info, dist, build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ tcg_market.db

run-backfill: ## Run backfill (use SET= and LIMIT= to customize)
	.venv/bin/python -m src.cli.main backfill $(if $(SET),--set $(SET)) $(if $(LIMIT),--limit $(LIMIT))

run-update: ## Run incremental update
	.venv/bin/python -m src.cli.main update
