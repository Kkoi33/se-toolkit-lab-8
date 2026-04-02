# Multi-stage Dockerfile for nanobot deployment
# Build context: ./nanobot with additional_contexts: workspace: ., webchat: ../nanobot-websocket-channel

# ---
# Stage 1: Build the application
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_SYSTEM_PACKAGES=1

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads, use system interpreter
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy root workspace files (from workspace context)
COPY --from=workspace pyproject.toml /app/pyproject.toml
COPY --from=workspace uv.lock /app/uv.lock

# Copy mcp directory (from workspace context)
COPY --from=workspace mcp /app/mcp

# Copy nanobot-websocket-channel (from webchat context)
COPY --from=webchat . /app/nanobot-websocket-channel

# Copy nanobot project files (from local context)
COPY . /app/nanobot

# Create virtual environment and install all packages
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install mcp first
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -e /app/mcp

# Install uv (for running MCP servers)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install uv

# Install nanobot
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -e /app/nanobot

# Install webchat channel plugin
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -e /app/nanobot-websocket-channel/nanobot-webchat

# Verify installation
RUN nanobot --version

# ---
# Stage 2: Final runtime image
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

# Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Create non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy the application from builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Set PATH and PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV UV_PYTHON_DOWNLOADS=0

# Use non-root user
USER nonroot

WORKDIR /app/nanobot

# Run the entrypoint which resolves config and launches gateway
CMD ["python", "/app/nanobot/entrypoint.py"]
