# F88 — Render Deploy Prep

**Status:** planned
**Created:** 2026-08-28
**Goal:** Deploy TEDHC Market as a single Render Web Service (backend API + frontend SPA), with gitflow (homol/main), production-ready config, and graceful degradation for heavy providers.

## Scope

- Gitflow: `homol` branch for dev/test, `main` for production (Render auto-deploy)
- Single Render Web Service: FastAPI serves both API and frontend static build
- Dockerfile with multi-stage build (Python + Node)
- render.yaml (Infrastructure as Code)
- Production uvicorn config (no reload, $PORT, workers)
- Liga provider disabled via env var (no Playwright on Render)
- Persistent Disk for SQLite at `/data/`
- CORS and API URL production config
- Documentation updates

## Architecture

```
Render Web Service
  Build: pip install . && cd frontend && npm ci && npm run build
  Start: uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port $PORT
  Disk:  /data (1GB, SQLite DB)

  Request flow:
    /api/v1/*  -> FastAPI routers
    /health    -> health check
    /*         -> frontend/dist/ (SPA catch-all)
```

## Tasks

| Task | Description | Wave | Depends |
|------|-------------|------|---------|
| T01  | Gitflow setup (homol branch + CLAUDE.md) | 0 | — |
| T02  | Production uvicorn config | 0 | — |
| T03  | Liga provider graceful degradation | 0 | — |
| T04  | Frontend static serving via FastAPI | 1 | — |
| T05  | CORS + API URL production config | 1 | — |
| T06  | Dockerfile (multi-stage) | 2 | T02,T03,T04 |
| T07  | render.yaml + build script | 2 | T06 |
| T08  | Documentation (CLAUDE.md, README, deploy guide) | 3 | all |

## Waves

- **Wave 0** (3 tasks, parallel): T01, T02, T03
- **Wave 1** (2 tasks, parallel): T04, T05
- **Wave 2** (2 tasks, parallel): T06, T07
- **Wave 3** (1 task): T08
