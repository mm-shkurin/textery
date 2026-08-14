# Backend image, built from THIS directory as the context.
#
# The monorepo has a second copy at infra/docker/backend.Dockerfile whose context
# is the repo root, because it builds alongside the frontend and nginx. This one
# is what makes the published repository self-contained: `docker build .` here
# needs nothing outside it. Keep the two in step -- they install the same runtime
# dependencies and run the same command.
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

# requirements.txt only, never requirements-dev.txt: the container runs the app,
# not the test suite, and pytest/ruff/mypy in a production image are weight and
# attack surface for tooling that never executes there.
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# The layer roots, copied separately so a change in one does not invalidate the
# cached layers of the others.
COPY domain domain
COPY usecase usecase
COPY adapters adapters
COPY application application

EXPOSE 8000

# Migrate, then serve. alembic.ini's script_location is relative, so alembic must
# run with cwd = adapters/db.
CMD ["sh", "-c", "cd adapters/db && alembic upgrade head && cd /app && uvicorn app.main:app --app-dir application/src --host 0.0.0.0 --port 8000"]

# Probes /health, which the app owns and which actually checks its dependencies
# (router/health/health_router.py answers 503 when one is down). Probing
# /openapi.json instead would report healthy from a process whose database is
# unreachable -- it tests that uvicorn accepts sockets and nothing more.
HEALTHCHECK --interval=30s --timeout=3s --retries=5 --start-period=15s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1
