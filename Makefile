.DEFAULT_GOAL := help

.PHONY: help setup config train resume run test test-unit lint clean checkpoints

help:
	@echo ""
	@echo "  TradingZero — Makefile"
	@echo ""
	@echo "  Setup"
	@echo "    make setup       Install dependencies via uv"
	@echo "    make config      Copy config.yaml.example -> config.yaml"
	@echo ""
	@echo "  Run"
	@echo "    make train       Start training from scratch (ignores existing checkpoint)"
	@echo "    make resume      Resume training from best checkpoint"
	@echo "    make run         Run best checkpoint inference"
	@echo "    make run CHECKPOINT=agent/checkpoints/gen_0200.zip"
	@echo ""
	@echo "  Dev"
	@echo "    make test        Run all tests with coverage"
	@echo "    make test-unit   Run unit tests only"
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

train:
	uv run python main.py --no-resume

resume:
	uv run python main.py

CHECKPOINT ?= agent/checkpoints/best.zip
run:
	uv run python run_best.py --checkpoint $(CHECKPOINT)

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

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
