# Hibanako

Every weld, every cert, one thread.

Hibanako reads a welded-fabrication dossier — mill certificates, WPS/PQR and welder
qualifications, production records, inspection drawings and NDT reports — with Google Gemini,
links every weld back to its heat number and NDT evidence, runs the release rules and produces a
signed traceability report.

| Folder | What it is |
| --- | --- |
| [`backend/`](backend/README.md) | Litestar API, arq worker, Postgres models, Alembic migrations, Gemini extraction and rules |
| [`frontend/`](frontend/README.md) | Vue 3 + Vite + Tailwind web app (landing page, workspace, report) |
| [`example-docs/`](example-docs/README.md) | Synthetic sample dossiers to try uploads with |
| `docker-compose.yml` | The whole stack in Docker: Postgres, Redis, API, worker and web |
| `firebase.json` | Firebase Hosting config for the frontend |

```
browser ──► web (nginx / Firebase Hosting) ──► api (Litestar) ──► Postgres
                                                  │    ▲
                                                  ▼    │ WebSocket events
                                               Redis (queue + pub/sub)
                                                  │
                                                  ▼
                                               worker (arq) ──► Gemini, Cloud Storage
```

## Run everything with Docker

Requirements: Docker Desktop, a Gemini API key, a Cloud Storage bucket and a service-account key
that can write to it.

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

1. In `backend/.env`, set at least `GEMINI_API_KEY`, `HIBANAKO_JWT_SECRET`,
   `HIBANAKO_DOCUMENTS_BUCKET`, and `HIBANAKO_GOOGLE_CLIENT_ID` (for Google sign-in).
2. Put the service-account key at `backend/gcs-key.json`, or point `GCS_KEY_FILE` in `.env` at it.
   No bucket? Set `HIBANAKO_STORAGE_BACKEND=local` in `backend/.env` and keep any small JSON file at
   `GCS_KEY_FILE`.
3. In `.env`, set `VITE_GOOGLE_CLIENT_ID` to the same OAuth client ID.

```bash
docker compose up -d --build
docker compose exec api python -m app.demo
```

Open http://localhost:8080. The API runs its migrations on start; `app.demo` creates the demo
account and the three demo projects (HBK-DEMO-001 release, 002 hold, 003 reject).

For Google sign-in, add `http://localhost:8080` to **Authorized JavaScript origins** of the OAuth
client in Google Cloud Console.

Stop with `docker compose down` (add `-v` to also delete the database).

## Develop locally

```bash
cd backend
docker compose up -d db redis
uv sync
uv run alembic upgrade head
uv run python -m app.demo
uv run uvicorn app.main:app --reload --port 8000
uv run arq app.worker.WorkerSettings
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` and the WebSocket to port 8000).

## Deploy to Google Cloud

The frontend goes to **Firebase Hosting**; the backend goes to **Cloud Run**, with **Cloud SQL**
(Postgres), **Memorystore** (Redis) and **Cloud Storage**. Both live in this one repo: Firebase only
uploads `frontend/dist`, and Cloud Run builds only from `backend/`.

Replace `PROJECT`, `REGION` (e.g. `asia-southeast2`) and the passwords below.

### 1. One-time setup

```bash
gcloud config set project PROJECT
gcloud services enable run.googleapis.com sqladmin.googleapis.com redis.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com \
  iamcredentials.googleapis.com

gcloud artifacts repositories create hibanako --repository-format=docker --location=REGION

gcloud iam service-accounts create hibanako-api
SA=hibanako-api@PROJECT.iam.gserviceaccount.com
gcloud storage buckets create gs://PROJECT-hibanako-documents --location=REGION
gcloud storage buckets add-iam-policy-binding gs://PROJECT-hibanako-documents \
  --member=serviceAccount:$SA --role=roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding $SA \
  --member=serviceAccount:$SA --role=roles/iam.serviceAccountTokenCreator
gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:$SA --role=roles/cloudsql.client
gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
```

The token-creator role lets the API sign the temporary download links without a key file.

### 2. Database and Redis

```bash
gcloud sql instances create hibanako-db --database-version=POSTGRES_17 --tier=db-f1-micro --region=REGION
gcloud sql databases create hibanako --instance=hibanako-db
gcloud sql users create hibanako --instance=hibanako-db --password=DB_PASSWORD

gcloud redis instances create hibanako-redis --size=1 --region=REGION
gcloud redis instances describe hibanako-redis --region=REGION --format='value(host)'
```

### 3. Secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(48), end='')" | gcloud secrets create hibanako-jwt --data-file=-
printf '%s' 'GEMINI_KEY' | gcloud secrets create hibanako-gemini --data-file=-
printf '%s' 'postgresql+asyncpg://hibanako:DB_PASSWORD@/hibanako?host=/cloudsql/PROJECT:REGION:hibanako-db' \
  | gcloud secrets create hibanako-db-url --data-file=-
```

### 4. API on Cloud Run

```bash
IMAGE=REGION-docker.pkg.dev/PROJECT/hibanako/backend
gcloud builds submit backend --tag $IMAGE

gcloud run deploy hibanako-api --image $IMAGE --region REGION --service-account $SA \
  --allow-unauthenticated --port 8000 --timeout 3600 \
  --add-cloudsql-instances PROJECT:REGION:hibanako-db \
  --network default --subnet default --vpc-egress private-ranges-only \
  --set-secrets HIBANAKO_DATABASE_URL=hibanako-db-url:latest,HIBANAKO_JWT_SECRET=hibanako-jwt:latest,GEMINI_API_KEY=hibanako-gemini:latest \
  --set-env-vars "^@^HIBANAKO_REDIS_URL=redis://REDIS_HOST:6379/0@HIBANAKO_DOCUMENTS_BUCKET=PROJECT-hibanako-documents@HIBANAKO_GOOGLE_CLIENT_ID=OAUTH_CLIENT_ID@HIBANAKO_CORS_ORIGINS=[\"https://PROJECT.web.app\"]"
```

The container runs `alembic upgrade head` before it starts, so migrations apply on every deploy.
`--timeout 3600` keeps the live-update WebSocket open for up to an hour (the app reconnects).

### 5. Worker

The worker has no HTTP port, so it runs as a Cloud Run **worker pool** from the same image:

```bash
gcloud beta run worker-pools deploy hibanako-worker --image $IMAGE --region REGION \
  --service-account $SA --command arq --args app.worker.WorkerSettings \
  --add-cloudsql-instances PROJECT:REGION:hibanako-db \
  --network default --subnet default --vpc-egress private-ranges-only \
  --set-secrets HIBANAKO_DATABASE_URL=hibanako-db-url:latest,HIBANAKO_JWT_SECRET=hibanako-jwt:latest,GEMINI_API_KEY=hibanako-gemini:latest \
  --set-env-vars HIBANAKO_REDIS_URL=redis://REDIS_HOST:6379/0,HIBANAKO_DOCUMENTS_BUCKET=PROJECT-hibanako-documents
```

If worker pools are not available in your region, run the same image on a small Compute Engine VM
with `docker run ... arq app.worker.WorkerSettings`.

Demo data, once: run the image as a Cloud Run job with `--command python --args=-m,app.demo`,
or `python -m app.demo` locally against the Cloud SQL Auth Proxy.

### 6. Frontend on Firebase Hosting

```bash
npm install -g firebase-tools
firebase login
firebase use --add PROJECT
```

Create `frontend/.env.production.local` (git-ignored):

```
VITE_API_URL=https://hibanako-api-xxxxxxxx.REGION.run.app
VITE_GOOGLE_CLIENT_ID=OAUTH_CLIENT_ID
```

Then, from the repo root:

```bash
firebase deploy --only hosting
```

`firebase.json` builds `frontend/` and uploads only `frontend/dist`; the backend folder is never
uploaded. The app calls the API and its WebSocket directly at `VITE_API_URL`, so make sure
`HIBANAKO_CORS_ORIGINS` on the API lists the Firebase domains (`https://PROJECT.web.app`, plus any
custom domain).

### 7. Google sign-in

In Google Cloud Console → APIs & Services → Credentials → your OAuth client, add the Firebase URLs
(`https://PROJECT.web.app`, `https://PROJECT.firebaseapp.com`, custom domain) to
**Authorized JavaScript origins**. To allow only your company, set
`HIBANAKO_GOOGLE_ALLOWED_DOMAINS=["company.com"]` on the API.

### Checklist

- [ ] New `HIBANAKO_JWT_SECRET` (never reuse the development one)
- [ ] `HIBANAKO_CORS_ORIGINS` = the Firebase / custom domains
- [ ] OAuth JavaScript origins include the production domains
- [ ] Bucket is private; the API service account has object admin and token creator
- [ ] Paid Gemini key for real customer documents
- [ ] `python -m app.demo` run once if the demo button should work
