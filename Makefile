
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync

# Install with dev dependencies
install-dev:
	uv sync --dev

# ==============================================================================
# Local Development
# ==============================================================================

# Run cocktail MCP server locally
run-cocktail-mcp:
	uv run python src/mcp_servers/cocktail_mcp_server/server.py

# Run weather MCP server locally
run-weather-mcp:
	uv run python src/mcp_servers/weather_mcp_server/server.py

# Run frontend locally
run-frontend:
	cd src/frontend && uv run python main.py

# ==============================================================================
# Agent Deployment
# ==============================================================================

# Deploy all agents (cocktail, weather, hosting) to Vertex AI Agent Engine
deploy-agents:
	uv run python deployment/deploy_agents.py

# ==============================================================================
# Infrastructure Setup
# ==============================================================================

# Initialize Terraform for main environment
terraform-init:
	cd deployment/terraform && terraform init

# Plan Terraform changes
terraform-plan:
	cd deployment/terraform && terraform plan

# Apply Terraform changes
terraform-apply:
	cd deployment/terraform && terraform apply

# Set up dev environment using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit tests
test-unit:
	uv sync --dev
	uv run pytest tests/unit

# Run integration tests
test-integration:
	uv sync --dev
	uv run pytest tests/integration

# Run all tests (unit + integration)
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration

# Run load tests
test-load:
	uv sync --dev
	uv run python tests/load_test/load_test.py

# Run code quality checks (codespell, ruff)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff

# Auto-fix lint issues
lint-fix:
	uv sync --dev --extra lint
	uv run ruff check . --fix
	uv run ruff format .

# ==============================================================================
# Agent Evaluation
# ==============================================================================

# Run agent evaluation
# Usage: make eval [EVALSET=tests/eval/evalsets/basic.evalset.json] [EVAL_CONFIG=tests/eval/eval_config.json]
eval:
	uv sync --dev --extra eval
	uv run python tests/eval/run_evaluation.py $${EVALSET:-tests/eval/evalsets/basic.evalset.json} \
		$(if $(EVAL_CONFIG),--config $(EVAL_CONFIG),$(if $(wildcard tests/eval/eval_config.json),--config tests/eval/eval_config.json,))

# ==============================================================================
# Docker
# ==============================================================================

# Build cocktail MCP server Docker image
docker-build-cocktail-mcp:
	docker build -t cocktail-mcp-server -f src/mcp_servers/cocktail_mcp_server/Dockerfile src/mcp_servers/cocktail_mcp_server/

# Build weather MCP server Docker image
docker-build-weather-mcp:
	docker build -t weather-mcp-server -f src/mcp_servers/weather_mcp_server/Dockerfile src/mcp_servers/weather_mcp_server/

# Build frontend Docker image
docker-build-frontend:
	docker build -t frontend -f src/frontend/Dockerfile src/frontend/

# Build all Docker images
docker-build-all: docker-build-cocktail-mcp docker-build-weather-mcp docker-build-frontend

# ==============================================================================
# Cleanup
# ==============================================================================

# Clean build artifacts and caches
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .ruff_cache/

.PHONY: install install-dev run-cocktail-mcp run-weather-mcp run-frontend \
	deploy-agents terraform-init terraform-plan terraform-apply setup-dev-env \
	test test-unit test-integration test-load lint lint-fix eval \
	docker-build-cocktail-mcp docker-build-weather-mcp docker-build-frontend docker-build-all \
	clean
