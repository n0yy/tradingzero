.DEFAULT_GOAL := help

.PHONY: help setup config backend backend-dev frontend frontend-build tui dev dev-fake db-migrate db-revision train resume run test test-unit test-issue-25 test-migration-gate lint clean checkpoints

help:
	@echo ""
	@echo "  TradingZero — Makefile"
	@echo ""
	@echo "  Setup"
	@echo "    make setup       Install dependencies via uv"
	@echo "    make config      Copy config.yaml.example -> config.yaml"
	@echo ""
	@echo "  Run"
	@echo "    make backend     Start web backend (FastAPI)"
	@echo "    make backend-dev Start web backend with auto-reload"
	@echo "    make frontend    Start frontend dev server (Vite)"
	@echo "    make tui         Start terminal TUI secondary interface"
	@echo "    make dev         Run backend + frontend together"
	@echo "    make dev-fake    Run backend + frontend with fake in-memory training stream"
	@echo "    make frontend-build Build frontend production assets"
	@echo "    make db-migrate  Apply Alembic migrations"
	@echo "    make db-revision MSG='add table'  Create new Alembic revision"
	@echo "    make train       Alias to backend (web cutover)"
	@echo "    make resume      Alias to backend (web cutover)"
	@echo "    make run         Run best checkpoint inference"
	@echo "    make run CHECKPOINT=agent/checkpoints/gen_0200.zip"
	@echo ""
	@echo "  Dev"
	@echo "    make test        Run all tests with coverage"
	@echo "    make test-unit   Run unit tests only"
	@echo "    make test-migration-gate Run backend+frontend+tui+e2e smoke gate"
	@echo "    make lint        Check code style (ruff)"
	@echo "    make clean       Remove cache and build artifacts"
	@echo "    make checkpoints List saved checkpoints"
	@echo ""

setup:
	uv sync

config:
	@if [ -f config.yaml ]; then \
		echo "config.yaml already exists — skipping. Delete it first to reset."; \
	else \
		cp config.yaml.example config.yaml; \
		echo "config.yaml created. Edit it before running."; \
	fi

backend:
	uv run python main.py

backend-dev:
	uv run python main.py --reload

frontend:
	cd apps/web && npm run dev

tui:
	uv run python -m apps.tui.main

frontend-build:
	cd apps/web && npm run build

dev:
	@trap 'kill 0' INT TERM EXIT; \
	(uv run python main.py --reload) & \
	(cd apps/web && npm run dev) & \
	wait

dev-fake:
	@trap 'kill 0' INT TERM EXIT; \
	(TRADINGZERO_RUNNER_MODE=inmemory uv run python main.py --reload) & \
	(cd apps/web && npm run dev) & \
	wait

db-migrate:
	uv run alembic upgrade head

db-revision:
	@test -n "$(MSG)" || (echo "MSG is required. Example: make db-revision MSG='add runs table'" && exit 1)
	uv run alembic revision --autogenerate -m "$(MSG)"

train:
	uv run python main.py

resume:
	uv run python main.py

CHECKPOINT ?= agent/checkpoints/best.zip
run:
	uv run python run_best.py --checkpoint $(CHECKPOINT)

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-migration-gate:
	uv run pytest --no-cov -q \
		tests/unit/test_app_bootstrap_env.py \
		tests/unit/test_main.py \
		tests/unit/test_web_app.py \
		tests/unit/test_run_lifecycle_api.py \
		tests/unit/test_run_history_retry_api.py \
		tests/unit/test_config_revision_api.py \
		tests/unit/test_tui_secondary_path.py \
		tests/integration/test_retry_recovery_flow.py \
		tests/integration/test_config_revision_startup_flow.py
	cd apps/web && npm test -- --run App.test.tsx
	cd apps/web && npm run e2e:smoke

lint:
	uv run ruff check . || true

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

checkpoints:
	@echo ""
	@echo "  Saved checkpoints:"
	@ls -lh agent/checkpoints/*.zip 2>/dev/null || echo "  No checkpoints found."
	@echo ""
