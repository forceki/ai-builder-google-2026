# Deploying Hibanako to Google Cloud

The frontend goes to **Firebase Hosting**; the backend goes to **Cloud Run**, with **Cloud SQL**
(Postgres), **Cloud Tasks** (background jobs) and **Cloud Storage**. There is no Redis and no separate
worker: Cloud Tasks calls the API back at `POST /tasks/<job>` with a Google-signed token, and the API runs
the job. Both live in this one repo: Firebase only uploads `frontend/dist`, and Cloud Run builds only from
`backend/`.

Replace `PROJECT`, `REGION` (e.g. `asia-southeast1`) and the passwords below.

## 1. One-time setup

```bash
gcloud config set project PROJECT
gcloud services enable run.googleapis.com sqladmin.googleapis.com cloudtasks.googleapis.com \
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
gcloud iam service-accounts add-iam-policy-binding $SA \
  --member=serviceAccount:$SA --role=roles/iam.serviceAccountUser
gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:$SA --role=roles/cloudsql.client
gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:$SA --role=roles/cloudtasks.enqueuer
```

| Role | Why |
| --- | --- |
| `storage.objectAdmin` on the bucket | Upload and read documents |
| `serviceAccountTokenCreator` on itself | Sign the temporary download links without a key file |
| `serviceAccountUser` on itself | Attach its own identity to each Cloud Task, so `/tasks` can verify the caller |
| `cloudsql.client` | Connect to the database |
| `secretmanager.secretAccessor` | Read the secrets |
| `cloudtasks.enqueuer` | Create tasks |

## 2. Database and job queue

```bash
gcloud sql instances create hibanako-db --database-version=POSTGRES_17 --edition=ENTERPRISE \
  --tier=db-f1-micro --region=REGION --availability-type=zonal --storage-type=SSD --storage-size=10 \
  --no-storage-auto-increase --no-enable-point-in-time-recovery
gcloud sql databases create hibanako --instance=hibanako-db
gcloud sql users create hibanako --instance=hibanako-db --password=DB_PASSWORD

gcloud tasks queues create hibanako-jobs --location=REGION \
  --max-concurrent-dispatches=4 --max-attempts=3 --min-backoff=10s
```

The queue reads at most 4 documents at a time and retries a failed job up to 3 times.

## 3. Secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(48), end='')" | gcloud secrets create hibanako-jwt --data-file=-
printf '%s' 'GEMINI_KEY' | gcloud secrets create hibanako-gemini --data-file=-
printf '%s' 'postgresql+asyncpg://hibanako:DB_PASSWORD@/hibanako?host=/cloudsql/PROJECT:REGION:hibanako-db' \
  | gcloud secrets create hibanako-db-url --data-file=-
```

## 4. API on Cloud Run

Settings file `run-env.yaml` (keep it outside the repo):

```yaml
HIBANAKO_STORAGE_BACKEND: "gcs"
HIBANAKO_DOCUMENTS_BUCKET: "PROJECT-hibanako-documents"
HIBANAKO_GCP_PROJECT: "PROJECT"
HIBANAKO_GOOGLE_CLIENT_ID: "OAUTH_CLIENT_ID"
HIBANAKO_CORS_ORIGINS: '["https://PROJECT.web.app","https://PROJECT.firebaseapp.com"]'
HIBANAKO_TASKS_INLINE: "false"
HIBANAKO_TASKS_LOCATION: "REGION"
HIBANAKO_TASKS_QUEUE: "hibanako-jobs"
HIBANAKO_TASKS_SERVICE_ACCOUNT: "hibanako-api@PROJECT.iam.gserviceaccount.com"
HIBANAKO_TASKS_SERVICE_URL: "https://hibanako-api-xxxxx.REGION.run.app"
```

```bash
IMAGE=REGION-docker.pkg.dev/PROJECT/hibanako/backend:v1
docker build -t $IMAGE backend && docker push $IMAGE

gcloud run deploy hibanako-api --image $IMAGE --region REGION --service-account $SA \
  --allow-unauthenticated --port 8000 --timeout 3600 --memory 1Gi \
  --add-cloudsql-instances PROJECT:REGION:hibanako-db \
  --env-vars-file run-env.yaml \
  --set-secrets HIBANAKO_DATABASE_URL=hibanako-db-url:latest,HIBANAKO_JWT_SECRET=hibanako-jwt:latest,GEMINI_API_KEY=hibanako-gemini:latest
```

On the very first deploy the service URL is not known yet: deploy once, copy the URL it prints into
`HIBANAKO_TASKS_SERVICE_URL`, and run the same deploy command again.

The container runs `alembic upgrade head` before it starts, so migrations apply on every deploy.
`--timeout 3600` keeps the live-update WebSocket open for up to an hour (the app reconnects).
The API scales to zero when idle; Cloud Tasks wakes it up when there is work.

## 5. Demo data

Run the image once as a Cloud Run job:

```bash
gcloud run jobs create hibanako-demo --image $IMAGE --region REGION --service-account $SA \
  --command python --args=-m,app.demo --set-cloudsql-instances PROJECT:REGION:hibanako-db \
  --env-vars-file run-env.yaml \
  --set-secrets HIBANAKO_DATABASE_URL=hibanako-db-url:latest,HIBANAKO_JWT_SECRET=hibanako-jwt:latest,GEMINI_API_KEY=hibanako-gemini:latest
gcloud run jobs execute hibanako-demo --region REGION --wait
```

## 6. Frontend on Firebase Hosting

```bash
npm install -g firebase-tools
firebase login
firebase use --add PROJECT
```

Create `frontend/.env.production.local` (git-ignored):

```
VITE_API_URL=https://hibanako-api-xxxxx.REGION.run.app
VITE_GOOGLE_CLIENT_ID=OAUTH_CLIENT_ID
```

Then, from the repo root:

```bash
firebase deploy --only hosting
```

`firebase.json` runs `npm run build` in `frontend/` (run `npm install` there first) and uploads only
`frontend/dist`; the backend folder is never uploaded. The app calls the API and its WebSocket directly at
`VITE_API_URL`, so `HIBANAKO_CORS_ORIGINS` on the API must list the Firebase domains.

## 7. Google sign-in

In Google Cloud Console → APIs & Services → Credentials → your OAuth client, add the Firebase URLs
(`https://PROJECT.web.app`, `https://PROJECT.firebaseapp.com`, custom domain) to
**Authorized JavaScript origins**. To allow only your company, set
`HIBANAKO_GOOGLE_ALLOWED_DOMAINS=["company.com"]` on the API.

## Cost

Cloud SQL (db-f1-micro, 10 GB SSD) is the only always-on service, about US$13 a month in Singapore.
Cloud Run and Cloud Tasks stay inside their free tiers at demo traffic. Stop the database between demos
with `gcloud sql instances patch hibanako-db --activation-policy=NEVER` (and `ALWAYS` to start it again).

## Checklist

- [ ] New `HIBANAKO_JWT_SECRET` (never reuse the development one)
- [ ] `HIBANAKO_TASKS_SERVICE_URL` is the deployed API URL, `HIBANAKO_TASKS_INLINE` is `false`
- [ ] `HIBANAKO_CORS_ORIGINS` = the Firebase / custom domains
- [ ] OAuth JavaScript origins include the production domains
- [ ] Bucket is private; the service account has the six roles above
- [ ] Paid Gemini key for real customer documents
- [ ] Demo job run once if the "Try the demo" button should work
