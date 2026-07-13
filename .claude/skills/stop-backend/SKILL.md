---
name: stop-backend
description: Stop the running backend application. Use when user wants to stop the backend server or mentions /stop-backend command.
---

# Stop Backend Application

## Action

If the backend was started as a background task (e.g. `npm run dev`/`uvicorn` invoked
directly), use `TaskStop` with its task ID.

If the backend is running via the compose stack (`/run-backend`'s default path):
```bash
docker compose -f infra/docker-compose.yml stop backend
```

## Output

Report: backend stopped.
