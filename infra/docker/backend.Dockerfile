# Real backend image: FastAPI app + Alembic migrations, run against the
# compose `postgres`/`redis` services. Build context is the repo root (see
# docker-compose.yml `backend.build.context: ..`) so this Dockerfile can COPY
# every backend/ module (domain, usecase, adapters/*, application) — main.py
# adds each module's src/ to sys.path itself (see application/src/app/main.py).
FROM python:3.12-slim

WORKDIR /app

# Native libraries WeasyPrint needs to rasterize text/vector output (Pango +
# cairo + harfbuzz + gdk-pixbuf), plus a font with Cyrillic coverage so Russian
# document content renders as glyphs, not tofu. Without these, `import weasyprint`
# fails at boot. Installed before pip so the wheel finds them at import time.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libharfbuzz0b \
      libgdk-pixbuf-2.0-0 \
      libffi8 \
      fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt only, never requirements-dev.txt. Until they were split on
# 2026-08-07 they were one file, so this line installed pytest, pytest-cov,
# pytest-mock, ruff, mypy and a stubs package into the production image -- weight
# and attack surface for tooling the container never runs.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/domain backend/domain
COPY backend/usecase backend/usecase
COPY backend/adapters backend/adapters
COPY backend/application backend/application

# The layer roots, inner-first — the same map pytest gets from pyproject.toml's
# `pythonpath`. This is what replaced nine sys.path.insert calls in the entry
# point: a package setup the interpreter is told about, rather than one the
# application patches at import time.
ENV PYTHONPATH=/app/backend/domain/src:/app/backend/usecase/src:/app/backend/adapters/rest/src:/app/backend/adapters/db/src:/app/backend/adapters/security/src:/app/backend/adapters/generation_provider/src:/app/backend/adapters/oauth_provider/src:/app/backend/adapters/rendering/src:/app/backend/application/src:/app/backend/application/src/app

EXPOSE 8000

# Apply migrations, then serve. alembic.ini's script_location is relative, so
# alembic must run with cwd = backend/adapters/db.
CMD ["sh", "-c", "cd backend/adapters/db && alembic upgrade head && cd /app && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# Probes /health, which the app owns and which actually checks its dependencies
# (router/health/health_router.py answers 503 when one is down).
#
# It used to probe /openapi.json, and two things were wrong with that. That route
# answers 200 from a process whose database is unreachable, so the container
# reported healthy while every request 500'd — it tested that uvicorn was
# accepting sockets and nothing else. And it is the most expensive GET the app
# serves: FastAPI builds the whole schema for it, and at a 10s interval that is
# 8 640 schema fetches a day, each one a log line burying everything else.
#
# Interval widened to 30s to match: this is a liveness probe, not a monitor.
# `compose up` still waits through start-period + retries.
HEALTHCHECK --interval=30s --timeout=3s --retries=5 --start-period=15s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1
