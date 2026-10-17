# Hibanako frontend

Vue 3 + Vite + Tailwind CSS v4, with Vuex and Vue Router.

| Path | What it is |
| --- | --- |
| `src/views/` | Landing, login, projects, workspace and report pages |
| `src/components/sections/` | Landing page sections (header, hero, process walkthrough, footer) |
| `src/components/workspace/` | Documents panel, trace map, inspector, sign-off banner |
| `src/components/ui/`, `src/components/app/` | Shared UI: brand stamp, dialogs, menus, app bar |
| `src/store/` | Vuex modules: auth, projects, workspace (polling + WebSocket) |
| `src/api/client.js` | API client and the live-update WebSocket |
| `public/` | Favicon, app icons, manifest, brand images |
| `nginx.conf`, `Dockerfile` | Production image |

## Run locally

```bash
npm install
npm run dev
```

http://localhost:5173 — Vite proxies `/api` (including the WebSocket) to the backend on port 8000.

## Environment

Put these in `.env.local` for development or `.env.production.local` for a production build
(both are git-ignored). They are baked in at build time.

| Variable | Notes |
| --- | --- |
| `VITE_GOOGLE_CLIENT_ID` | OAuth client ID for the Google sign-in button |
| `VITE_API_URL` | Backend URL, e.g. `https://hibanako-api-xxxx.run.app`. Leave empty when `/api` is served from the same origin (Vite dev server, nginx image) |
| `VITE_DEMO_EMAIL`, `VITE_DEMO_PASSWORD` | Demo account for "Try the demo"; defaults match the backend |

## Build

```bash
npm run build
npm run preview
```

## Docker

```bash
docker build -t hibanako-web --build-arg VITE_GOOGLE_CLIENT_ID=... .
docker run -p 8080:80 -e API_UPSTREAM=http://host.docker.internal:8000 hibanako-web
```

nginx serves the built app and forwards `/api` and the WebSocket to `API_UPSTREAM`
(default `http://api:8000`, the service name in the root `docker-compose.yml`).

## Firebase Hosting

`firebase.json` lives in the repo root and points at `frontend/dist`, so deploy from the root:

```bash
firebase use --add PROJECT
firebase deploy --only hosting
```

It runs `npm ci` and `npm run build` here first and uploads only the build output. Set
`VITE_API_URL` in `.env.production.local` to the Cloud Run API URL. Full steps are in the
[root README](../README.md#6-frontend-on-firebase-hosting).
