# Real backend image: FastAPI app + Alembic migrations, run against the
# compose `postgres`/`redis` services. Build context is the repo root (see
# docker-compose.yml `backend.build.context: ..`) so this Dockerfile can COPY
# every backend/ module (domain, usecase, adapters/*, application) — main.py
# adds each module's src/ to sys.path itself (see application/src/app/main.py).
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/domain backend/domain
COPY backend/usecase backend/usecase
COPY backend/adapters backend/adapters
COPY backend/application backend/application

EXPOSE 8000

# Apply migrations, then serve. alembic.ini's script_location is relative, so
# alembic must run with cwd = backend/adapters/db.
CMD ["sh", "-c", "cd backend/adapters/db && alembic upgrade head && cd /app && uvicorn app.main:app --app-dir backend/application/src --host 0.0.0.0 --port 8000"]

HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=15s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/openapi.json', timeout=2)" || exit 1
