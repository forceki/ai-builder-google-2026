# Hibanako backend

Litestar API with background jobs (Google Cloud Tasks when deployed, in-process locally). Python 3.12, managed with [uv](https://docs.astral.sh/uv/).

| Path | What it is |
| --- | --- |
| `app/main.py` | Litestar app, routes, JWT middleware, CORS |
| `app/api/` | HTTP and WebSocket handlers (auth, projects, documents, checks, sign-off, events, AI logs, `/tasks`) |
| `app/ai/` | Gemini client, document classification, extraction and finding explanations |
| `app/pipeline/` | Normalises extracted data and builds the trace map |
| `app/rules/` | Release rules (material traceability, weld linkage, NDT evidence, completeness) |
| `app/assessment/` | Welding assessment: conditions catalog, file sorting, sample dossier and the WPS/WPQ/PWHT rules engine |
| `app/models/` | SQLAlchemy models |
| `app/schemas/` | Pydantic schemas for extraction and the API |
| `app/jobs.py` | Background jobs: read a document, settle and run checks |
| `app/queue.py` | Job queue: in-process locally, Cloud Tasks when deployed |
| `app/demo.py` | Demo account and the three demo projects |
| `migrations/` | Alembic migrations |
| `tests/` | pytest suite |

## Run locally

```bash
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run python -m app.demo
uv run uvicorn app.main:app --reload --port 8000
```

Postgres listens on host port 5433, so it doesn't clash with a local install. Background jobs run inside
the API (`HIBANAKO_TASKS_INLINE=true`), four at a time. `docker compose up --build` in this folder also
runs the API in a container; the
[root compose file](../docker-compose.yml) adds the web app on top.

## Configuration

All settings are environment variables with the `HIBANAKO_` prefix, read from `.env`. See
[`.env.example`](.env.example) for the full list.

| Variable | Required | Notes |
| --- | --- | --- |
| `HIBANAKO_JWT_SECRET` | yes | At least 32 characters |
| `GEMINI_API_KEY` | yes | Gemini API key |
| `HIBANAKO_DATABASE_URL` | | Default `postgresql+asyncpg://heatmark:heatmark@localhost:5433/heatmark` |
| `HIBANAKO_STORAGE_BACKEND` | | `gcs` (default) or `local` |
| `HIBANAKO_DOCUMENTS_BUCKET` | | Cloud Storage bucket for uploads |
| `HIBANAKO_GCS_CREDENTIALS_FILE` | | Service-account key; unset = Application Default Credentials |
| `HIBANAKO_CORS_ORIGINS` | | JSON list of frontend origins |
| `HIBANAKO_GOOGLE_CLIENT_ID` | | OAuth client ID for Google sign-in |
| `HIBANAKO_GOOGLE_ALLOWED_DOMAINS` | | JSON list; empty = any Google account |
| `HIBANAKO_EXTRACT_MODEL` | | Default `gemini-3.8-flash` |
| `HIBANAKO_CHECKS_DEBOUNCE_SECONDS` | | Wait after the last upload before checks run (default 15) |
| `HIBANAKO_EXTRACT_TIMEOUT_SECONDS` | | A document that takes longer fails instead of hanging (default 120) |
| `HIBANAKO_TASKS_INLINE` | | `true` (default) = jobs run in the API; `false` = Google Cloud Tasks |
| `HIBANAKO_TASKS_SERVICE_URL` | with Cloud Tasks | The API's own URL; Cloud Tasks calls `<url>/tasks/<job>` |
| `HIBANAKO_TASKS_SERVICE_ACCOUNT` | with Cloud Tasks | Service account whose signed token `/tasks` accepts |
| `HIBANAKO_TASKS_QUEUE`, `HIBANAKO_TASKS_LOCATION` | | Default `hibanako-jobs`, `asia-southeast1` |

Deleting a file or project removes it from the database only; objects in Cloud Storage are kept.

## Commands

```bash
uv run python -m app.demo                 # demo account + HBK-DEMO-001..003
uv run python -m app.demo --reset         # recreate the demo projects
uv run python -m app.auth add-user you@company.com --name "Your Name"
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run pytest
uv run --with reportlab python -m scripts.make_example_documents   # regenerate ../example-docs (acceptable, not-acceptable)
uv run python -m scripts.eval_examples          # read ../example-docs with Gemini, check verdicts and planted defects
```

`scripts/eval_examples.py` caches each extraction in `var/eval-cache` by file hash, so re-runs only call Gemini for new
or changed files (`--refresh` reads everything again, `--folder NAME` limits it to one set). The generator writes the
same bytes on every run, so unchanged documents are not read again.

## Docker

```bash
docker build -t hibanako-backend .
docker run --env-file .env -p 8000:8000 hibanako-backend
```

The image runs `alembic upgrade head` and then uvicorn on `$PORT` (default 8000). There is no separate
worker: jobs run inside the API. Deployment to Cloud Run is described in the
[deploy guide](../docs/deploy.md).
