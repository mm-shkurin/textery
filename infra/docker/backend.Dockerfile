# TEMP placeholder — backend/ is empty until a separate session lands the real
# FastAPI app. This Dockerfile only proves the `backend`/`worker` services can
# build, boot, and reach Postgres/Redis. Replace once real code exists:
#   - COPY the real app (or bind-mount it — see infra/architecture.md) and
#     install its dependencies (requirements.txt / poetry / uv).
#   - Replace the CMD below with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
#   - Keep the `worker` service's `command:` override for the real
#     `arq worker.WorkerSettings` entrypoint (see docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

# No COPY: backend/ has no code yet.

EXPOSE 8000

# Trivial HTTP server so the `backend` service responds to something and the
# container has a real listening port to heal-check against.
CMD ["python3", "-m", "http.server", "8000"]

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=2)" || exit 1
