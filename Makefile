# ============================================================================
#  FastAPI Firestore Backend — Makefile
#  Usage: make <target>
#  Run `make help` to see all available commands
# ============================================================================

# Variables 
VENV          := .venv
PYTHON        := $(VENV)/bin/python3
PIP           := $(PYTHON) -m pip
APP_MODULE    := app.main:app
HOST          := 0.0.0.0
DEV_PORT      := 8000
LOG_LEVEL_DEV := debug
PYTEST        := $(PYTHON) -m pytest
RUFF          := $(PYTHON) -m ruff
MYPY          := $(PYTHON) -m mypy
COVERAGE      := $(PYTHON) -m coverage

# Colours for terminal output
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m
BOLD   := \033[1m
RESET  := \033[0m

#  Default target 
.DEFAULT_GOAL := help

# Mark targets that don't produce files
.PHONY: help \
        venv install install-dev update \
        dev test coverage lint format \
        docker-build docker-up docker-down docker-logs docker-shell \
        clean nuke env-check

# ============================================================================
#  HELP
# ============================================================================

help:
	@echo ""
	@echo "$(BOLD)$(CYAN)FastAPI Firestore Backend$(RESET)"
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@echo "$(BOLD)$(YELLOW) ENVIRONMENT$(RESET)"
	@echo "  $(GREEN)make venv$(RESET)              Create a virtual environment"
	@echo ""
	@echo "$(BOLD)$(YELLOW) DEPENDENCIES$(RESET)"
	@echo "  $(GREEN)make install$(RESET)           Install production dependencies"
	@echo "  $(GREEN)make install-dev$(RESET)       Install all dependencies (dev + prod)"
	@echo "  $(GREEN)make update$(RESET)            Update dependencies"
	@echo ""
	@echo "$(BOLD)$(YELLOW) RUN APPLICATION$(RESET)"
	@echo "  $(GREEN)make dev$(RESET)               Run API server locally (hot reload)"
	@echo ""
	@echo "$(BOLD)$(YELLOW) TESTING$(RESET)"
	@echo "  $(GREEN)make test$(RESET)              Run the full test suite"
	@echo ""
	@echo "$(BOLD)$(YELLOW) CODE QUALITY$(RESET)"
	@echo "  $(GREEN)make lint$(RESET)              Lint code with Ruff"
	@echo "  $(GREEN)make format$(RESET)            Format code with Ruff"
	@echo ""
	@echo "$(BOLD)$(YELLOW) DOCKER$(RESET)"
	@echo "  $(GREEN)make docker-build$(RESET)      Build Docker images"
	@echo "  $(GREEN)make docker-up$(RESET)         Start services in Docker (detached)"
	@echo "  $(GREEN)make docker-down$(RESET)       Stop and remove containers"
	@echo "  $(GREEN)make docker-logs$(RESET)       Tail logs from containers"
	@echo ""
	@echo "$(BOLD)$(YELLOW) UTILITIES$(RESET)"
	@echo "  $(GREEN)make env-check$(RESET)         Check if .env variables are set"
	@echo "  $(GREEN)make clean$(RESET)             Remove build artefacts and cache"
	@echo "  $(GREEN)make nuke$(RESET)               Full reset (clean + docker-down)"
	@echo ""

# ============================================================================
#  ENVIRONMENT
# ============================================================================

venv:
	@echo "$(CYAN)▶ Creating virtual environment in $(VENV)...$(RESET)"
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	@echo "$(GREEN)✔ Virtual environment created$(RESET)"
	@echo "$(YELLOW)  To activate: source $(VENV)/bin/activate$(RESET)"

# ============================================================================
#  DEPENDENCIES
# ============================================================================

install:
	@echo "$(CYAN)▶ Installing production dependencies...$(RESET)"
	$(PIP) install .
	@echo "$(GREEN)✔ Dependencies installed$(RESET)"

install-dev:
	@echo "$(CYAN)▶ Installing all dependencies (including dev)...$(RESET)"
	$(PIP) install ".[dev]"
	@echo "$(GREEN)✔ Development dependencies installed$(RESET)"

update:
	@echo "$(CYAN)▶ Updating dependencies...$(RESET)"
	$(PIP) install --upgrade . ".[dev]"
	@echo "$(GREEN)✔ Dependencies updated$(RESET)"

# ============================================================================
#  RUN APPLICATION
# ============================================================================

dev:
	@echo "$(CYAN)▶ Starting API in development mode...$(RESET)"
	@echo "$(YELLOW)  Swagger UI: http://localhost:$(DEV_PORT)/api/v1/docs$(RESET)"
	@echo "$(GREEN)✔ Application starting successfully...$(RESET)"
	$(PYTHON) -m uvicorn $(APP_MODULE) --host $(HOST) --port $(DEV_PORT) --reload --log-level $(LOG_LEVEL_DEV)

# ============================================================================
#  TESTING
# ============================================================================

test: install-dev
	@echo "$(CYAN)▶ Running tests...$(RESET)"
	$(PYTEST) tests/ -v

coverage: install-dev
	@echo "$(CYAN)▶ Running tests with coverage...$(RESET)"
	$(PYTHON) -m pytest --cov=app tests/
	$(COVERAGE) report -m
	$(COVERAGE) html
	@echo "$(GREEN)✔ Coverage report generated in htmlcov/index.html$(RESET)"

# ============================================================================
#  CODE QUALITY
# ============================================================================

lint:
	@echo "$(CYAN)▶ Linting with Ruff...$(RESET)"
	$(PYTHON) -m ruff check .
	@echo "$(GREEN)✔ Lint passed$(RESET)"

format:
	@echo "$(CYAN)▶ Formatting code with Ruff...$(RESET)"
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check . --fix
	@echo "$(GREEN)✔ Code formatted$(RESET)"

# ============================================================================
#  DOCKER
# ============================================================================

docker-build:
	@echo "$(CYAN)▶ Building Docker images...$(RESET)"
	docker compose build
	@echo "$(GREEN)✔ Images built$(RESET)"

docker-up:
	@echo "$(CYAN)▶ Starting services in Docker...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✔ Services running$(RESET)"

docker-down:
	@echo "$(YELLOW)▶ Stopping services...$(RESET)"
	docker compose down
	@echo "$(GREEN)✔ Services stopped$(RESET)"

docker-logs:
	docker compose logs -f

docker-shell:
	docker compose exec web /bin/bash

# ============================================================================
#  UTILITIES
# ============================================================================

env-check:
	@echo "$(CYAN)▶ Checking environment variables...$(RESET)"
	@if [ ! -f .env ]; then echo "$(RED)✘ .env file not found$(RESET)"; exit 1; fi
	@for var in FIREBASE_PROJECT_ID FIREBASE_CLIENT_EMAIL GEMINI_API_KEY; do \
		if ! grep -q "^$$var=" .env; then echo "$(RED)✘ Missing: $$var$(RESET)"; else echo "$(GREEN)✔ $$var$(RESET)"; fi \
	done
	@if grep -q "^FIREBASE_SERVICE_ACCOUNT_PATH=" .env; then echo "$(GREEN)✔ FIREBASE_SERVICE_ACCOUNT_PATH$(RESET)"; fi
	@if grep -q "^BACKEND_CORS_ORIGINS=" .env; then echo "$(GREEN)✔ BACKEND_CORS_ORIGINS$(RESET)"; fi

clean:
	@echo "$(CYAN)▶ Cleaning cache...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov
	@echo "$(GREEN)✔ Clean complete$(RESET)"

nuke: clean docker-down
	@echo "$(RED)▶ Performing full reset...$(RESET)"
	@echo "$(GREEN)✔ Reset complete$(RESET)"
