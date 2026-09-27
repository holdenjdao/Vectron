.PHONY: help install dev backend frontend test lint format build serve

# Per-task delay so you can watch the assembly line in the UI (0 = full speed).
PACING ?= 0.4

help:
	@echo "make install   install backend (uv) and frontend (npm) dependencies"
	@echo "make dev       API on :8000 + UI on :5173 with live reload"
	@echo "make test      backend tests + frontend typecheck"
	@echo "make lint      ruff lint + format check"
	@echo "make build     build the UI into frontend/dist"
	@echo "make serve     serve API + built UI on :8000"

install:
	cd backend && uv sync
	cd frontend && npm install

backend:
	cd backend && VECTRON_PACING_SECONDS=$(PACING) uv run vectron serve --reload

frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 backend frontend

test:
	cd backend && uv run pytest
	cd frontend && npm run typecheck

lint:
	cd backend && uv run ruff check src tests && uv run ruff format --check src tests

format:
	cd backend && uv run ruff format src tests && uv run ruff check --fix src tests

build:
	cd frontend && npm run build

serve: build
	cd backend && uv run vectron serve
