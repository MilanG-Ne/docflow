# Development

Docker Compose is the supported complete demo. For fast local development, use Python 3.12+, Node.js 24, pnpm 11.19.0, and a working headless LibreOffice installation. SQLite is the default local database; PostgreSQL is used in Compose and CI.

## Backend

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.lock
cd backend
mkdir -p data
../.venv/bin/python -m alembic upgrade head
DEMO_MODE=true ../.venv/bin/python -m docflow.seed
DEMO_MODE=true APP_ORIGIN=http://localhost:3001 ../.venv/bin/python -m uvicorn docflow.api:app --host 127.0.0.1 --port 8000
```

In another terminal, from `backend/`, run the worker:

```sh
../.venv/bin/python -m docflow.worker
```

If LibreOffice has a different executable name or path, set `LIBREOFFICE_BIN` for the worker. The API does not run conversions in request handlers.

## Frontend

From `frontend/`:

```sh
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1 --port 3001
```

Open [localhost:3001](http://localhost:3001). The development server proxies `/api` to port 8000; `APP_ORIGIN` on the API must match the browser's origin exactly. Use `localhost`, rather than mixing it with `127.0.0.1` in the browser address.

`pnpm build` exports static assets to `frontend/dist/client`. In Compose, FastAPI serves these assets and the API from the same origin on port 8000. A frontend-only preview cannot save proposals without the backend and worker.

## Checks

From `backend/`:

```sh
../.venv/bin/python -m ruff check .
../.venv/bin/python -m pytest -q
RUN_CONVERSION_TESTS=1 ../.venv/bin/python -m pytest -q
```

The first pytest command skips real LibreOffice conversion and PostgreSQL checks unless their environment variables are set. `RUN_CONVERSION_TESTS=1` enables conversion. `LIBREOFFICE_BIN` can point tests at a particular executable.

For concurrency tests, provide `TEST_POSTGRES_URL` using the `postgresql+psycopg://` scheme. Use a **separate disposable test database** whose user can create schemas. Each test creates and drops its own schema; do not use a production database. CI runs these tests against PostgreSQL 17 and checks `alembic upgrade head` followed by `alembic check`.

From `frontend/`:

```sh
pnpm check
pnpm test
pnpm build
```

Fee tests use Node's built-in test runner and TypeScript support. Frontend dependency versions are locked in `pnpm-lock.yaml`; Python runtime and test dependencies are in `requirements.lock` and `requirements-dev.lock`. Install the lockfiles to reproduce CI rather than resolving the broader package metadata ranges.

## Configuration

Settings are read from process environment variables, not automatically from a `.env` file.

| Variable | Default outside Compose | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/docflow.db` | SQLAlchemy database URL; paths are relative to the process directory |
| `ARTIFACT_DIR` | `./data/artifacts` | Generated files; API and worker must share it |
| `FRONTEND_DIR` | `../frontend/dist/client` | Static frontend build |
| `APP_ORIGIN` | `http://localhost:8000` | Accepted browser origin; use port 3001 for development |
| `DEMO_MODE` | `false` | Enable demo account selection and allow seeding |
| `COOKIE_SECURE` | `false` | Set true when using HTTPS |
| `LIBREOFFICE_BIN` | `libreoffice` | Worker conversion executable |

The interactive API reference is at [localhost:8000/api/docs](http://localhost:8000/api/docs). Login returns the CSRF value and sets a cookie; authenticated mutations require both the cookie and `X-CSRF-Token`. `scripts/smoke.py` is a complete standard-library client example.

## Troubleshooting

- **Conversion stays queued:** check `docker compose logs worker`. The API can start while the worker is processing seeded documents.
- **Generation failed:** read worker logs for the underlying converter error. Retry a transient failure from the latest draft. If the template changed, create a new revision.
- **Port 8000 is occupied:** stop the other local service. If changing the Compose port mapping, change `APP_ORIGIN` to the matching browser origin too.
- **Origin or session error:** use one browser hostname consistently, verify `APP_ORIGIN`, and sign in again.
- **Missing documents after restoring data:** restore the matching artifact volume as well as the database. The integrity check intentionally refuses changed or missing files.

`docker compose down` preserves data. `docker compose down --volumes` deletes the demo database and generated documents permanently. There are no automatic cloud deployments or paid services in these commands.
