---
name: run-frontend
description: Start the frontend dev server. Use when user wants to start the frontend or mentions /run-frontend command.
---

# Run Frontend Dev Server

## Prerequisite

Ensure `infra/.env` exists (copy from `infra/.env.example` if not — no generator script,
see `infra/architecture.md`).

## Action

Start the frontend service via the real compose stack:
```bash
docker compose -f infra/docker-compose.yml up -d --build frontend
```

This builds the Vite app and serves it via nginx (see `infra/architecture.md`'s
`frontend.Dockerfile` notes) — not a hot-reload dev server. For local hot-reload
development instead, run `npm run dev` directly inside `frontend/`.

Port comes from `FRONTEND_PORT` in `infra/.env` (default `80` for the compose route,
Vite's own default for `npm run dev`).

## Output

Report startup status. App runs at `http://localhost:{FRONTEND_PORT}` (from `infra/.env`).

Stop with `docker compose -f infra/docker-compose.yml stop frontend`.
