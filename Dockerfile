FROM node:24-bookworm-slim AS frontend
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@11.19.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-liberation2 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /data/artifacts && chown -R app:app /data
WORKDIR /app/backend
COPY backend/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/docflow ./docflow
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY examples /app/examples
COPY scripts /app/scripts

FROM base AS test
COPY backend/requirements-dev.lock ./requirements-dev.lock
RUN pip install --no-cache-dir -r requirements-dev.lock
COPY backend/tests ./tests
COPY backend/pyproject.toml ./
USER app
ENV RUN_CONVERSION_TESTS=1
CMD ["python", "-m", "pytest", "-q"]

FROM base AS runtime
COPY --from=frontend /build/dist/client /app/frontend
USER app
ENV FRONTEND_DIR=/app/frontend ARTIFACT_DIR=/data/artifacts
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "docflow.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
