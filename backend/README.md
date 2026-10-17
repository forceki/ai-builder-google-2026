# Hibanako backend

Litestar API and arq worker. Python 3.12, managed with [uv](https://docs.astral.sh/uv/).

| Path | What it is |
| --- | --- |
| `app/main.py` | Litestar app, routes, JWT middleware, CORS |
| `app/api/` | HTTP and WebSocket handlers (auth, projects, documents, checks, sign-off, events, AI logs) |
| `app/ai/` | Gemini client, document classification, extraction and finding explanations |
| `app/pipeline/` | Normalises extracted data and builds the trace map |
| `app/rules/` | Release rules (material traceability, weld linkage, NDT evidence, completeness) |
| `app/models/` | SQLAlchemy models |
| `app/schemas/` | Pydantic schemas for extraction and the API |
| `app/worker.py` | arq jobs: read a document, settle and run checks |
| `app/demo.py` | Demo account and the three demo projects |
| `migrations/` | Alembic migrations |
| `tests/` | pytest suite |

## Run locally

```bash
cp .env.example .env
docker compose up -d db redis
uv sync
uv run alembic upgrade head
uv run python -m app.demo
uv run uvicorn app.main:app --reload --port 8000
uv run arq app.worker.WorkerSettings
```

Postgres listens on host port 5433 and Redis on 6380, so they don't clash with local installs.
`docker compose up --build` in this folder also runs the API and worker in containers; the
[root compose file](../docker-compose.yml) adds the web app on top.

## Configuration

All settings are environment variables with the `HIBANAKO_` prefix, read from `.env`. See
[`.env.example`](.env.example) for the full list.

| Variable | Required | Notes |
| --- | --- | --- |
| `HIBANAKO_JWT_SECRET` | yes | At least 32 characters |
| `GEMINI_API_KEY` | yes | Gemini API key |
| `HIBANAKO_DATABASE_URL` | | Default `postgresql+asyncpg://heatmark:heatmark@localhost:5433/heatmark` |
| `HIBANAKO_REDIS_URL` | | Default `redis://localhost:6380/0` |
| `HIBANAKO_STORAGE_BACKEND` | | `gcs` (default) or `local` |
| `HIBANAKO_DOCUMENTS_BUCKET` | | Cloud Storage bucket for uploads |
| `HIBANAKO_GCS_CREDENTIALS_FILE` | | Service-account key; unset = Application Default Credentials |
| `HIBANAKO_CORS_ORIGINS` | | JSON list of frontend origins |
| `HIBANAKO_GOOGLE_CLIENT_ID` | | OAuth client ID for Google sign-in |
| `HIBANAKO_GOOGLE_ALLOWED_DOMAINS` | | JSON list; empty = any Google account |
| `HIBANAKO_EXTRACT_MODEL` | | Default `gemini-3.8-flash` |
| `HIBANAKO_CHECKS_DEBOUNCE_SECONDS` | | Wait after the last upload before checks run (default 15) |

Deleting a file or project removes it from the database only; objects in Cloud Storage are kept.

## Commands

```bash
uv run python -m app.demo                 # demo account + HBK-DEMO-001..003
uv run python -m app.demo --reset         # recreate the demo projects
uv run python -m app.auth add-user you@company.com --name "Your Name"
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run pytest
```

## Docker

```bash
docker build -t hibanako-backend .
docker run --env-file .env -p 8000:8000 hibanako-backend
docker run --env-file .env hibanako-backend arq app.worker.WorkerSettings
```

The image runs `alembic upgrade head` and then uvicorn on `$PORT` (default 8000). The same image
is used for the worker by overriding the command. Deployment to Cloud Run is described in the
[root README](../README.md#deploy-to-google-cloud).
