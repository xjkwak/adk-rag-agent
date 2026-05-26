ifeq ($(wildcard pyproject.toml),)
$(error Run make from the repository root (directory that contains pyproject.toml). Current directory: $(CURDIR))
endif

# Backend port for `adk api_server` and the Vite dev proxy (override if 8000 is busy).
ADK_API_PORT ?= 8000
export ADK_API_PORT

# Set USE_LOCAL_RAG=1 in knowledge_hub/.env for Chroma-backed RAG (see README).

install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync --extra dev && npm --prefix frontend install

dev:
	@$(MAKE) dev-backend &
	@echo "Waiting for ADK API on 127.0.0.1:$(ADK_API_PORT)..."
	@for i in $$(seq 1 120); do \
	  if nc -z 127.0.0.1 $(ADK_API_PORT) 2>/dev/null; then \
	    echo "Backend is up."; \
	    $(MAKE) dev-frontend; \
	    exit $$?; \
	  fi; \
	  sleep 0.25; \
	done; \
	echo "Timed out waiting for the backend on port $(ADK_API_PORT)."; \
	echo "If the port is in use, try: ADK_API_PORT=8001 make dev"; \
	exit 1

dev-backend:
	uv run adk api_server . --allow_origins="*" --port $(ADK_API_PORT)

dev-frontend:
	npm --prefix frontend run dev

playground:
	uv run adk web --port 8501

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .
