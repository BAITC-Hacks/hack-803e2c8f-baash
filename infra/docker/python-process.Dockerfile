FROM ghcr.io/astral-sh/uv:0.11.28 AS uv

FROM python:3.12.14-slim-trixie@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system --gid 10001 pulse109 \
    && useradd --system --uid 10001 --gid pulse109 --home-dir /nonexistent pulse109

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY services ./services
COPY adapters ./adapters
COPY contracts ./contracts
# Optional extras for a deployment, empty by default. A local or demo image
# carries no cloud SDK, so nothing here can start depending on one by accident.
ARG PULSE109_EXTRAS=""
RUN if [ -n "$PULSE109_EXTRAS" ]; then \
      uv sync --frozen --no-dev --extra "$PULSE109_EXTRAS"; \
    else \
      uv sync --frozen --no-dev; \
    fi

# /app belongs to root, but the process runs as pulse109. The replay snapshot
# store creates .data/snapshots at import, so it must exist and be writable by
# the runtime user before privileges drop. Without this the container raises
# PermissionError on '.data' and exits 1, taking the whole topology down.
RUN mkdir -p /app/.data/snapshots /app/.data/attachments \
    && chown -R pulse109:pulse109 /app/.data

USER pulse109
EXPOSE 8080
CMD ["uvicorn", "pulse109.main:app", "--host", "0.0.0.0", "--port", "8080"]
