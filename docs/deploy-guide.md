# Deploy Guide — TEDHC Market on Render

## Prerequisites

- GitHub repo connected to Render
- Render account (free tier works)

## Option A: Blueprint (recommended)

1. Go to Render Dashboard → **New** → **Blueprint**
2. Connect your repo, select branch `main`
3. Render reads `render.yaml` and auto-creates:
   - Web Service (Docker, free plan)
   - Persistent Disk (1GB at `/data`)
   - Environment variables (JWT secret auto-generated)
4. After first deploy, set `TCG_CORS_ORIGINS`:
   - Go to Service → Environment → add `TCG_CORS_ORIGINS=https://your-app.onrender.com`

## Option B: Manual setup

1. **New Web Service** → Docker → branch `main`
2. **Build:** uses `Dockerfile` (multi-stage: Node frontend + Python backend)
3. **Start:** `render-start.sh` (seeds data + starts uvicorn)
4. **Health check:** `/health`
5. **Persistent Disk:** Add disk, mount at `/data`, 1GB
6. **Environment variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TCG_ENV` | Yes | `development` | Set to `production` |
| `TCG_JWT_SECRET` | Yes | — | Random secret for JWT signing |
| `TCG_DATABASE_URL` | Yes | `sqlite:///tcg_market.db` | Use `sqlite:////data/tcg_market.db` |
| `TCG_CORS_ORIGINS` | Yes | `http://localhost:5173` | Your Render URL |
| `TCG_LIGA_DISABLED` | No | `0` | Set `1` to skip Playwright |
| `TCG_SCHEDULER_DISABLED` | No | `0` | Set `1` to disable cron jobs |
| `TCG_ERROR_LOG_DIR` | No | `logs/errors` | Use `/data/logs/errors` on Render |
| `PORT` | Auto | `8000` | Set by Render automatically |

## Promoting homol → main

1. Validate changes on `homol` branch (local testing)
2. When ready: `git checkout main && git merge homol && git push`
3. Render auto-deploys from `main`

## Troubleshooting

- **502 on first deploy:** wait for build to complete + health check to pass
- **SQLite locked:** ensure only 1 worker (default in Dockerfile)
- **CORS errors:** verify `TCG_CORS_ORIGINS` matches your Render URL exactly
- **Liga endpoints 503:** expected when `TCG_LIGA_DISABLED=1`
- **DB lost after deploy:** ensure Persistent Disk is mounted at `/data`
