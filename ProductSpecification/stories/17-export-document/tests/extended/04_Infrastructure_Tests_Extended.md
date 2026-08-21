> These are additional edge case tests. Implement after core tests pass.

# Export document — Infrastructure Tests (Extended)

Native render dependencies of the built image.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике` |
| Image under test | the backend image built from `backend/Dockerfile` |
| Native render libs | `libpango-1.0`, `libcairo`, `libgdk_pixbuf-2.0` (WeasyPrint's system dependencies) |
| Compose file | `infra/docker-compose.yml`; ports read from `infra/.env`, never hardcoded |

## 1. Image Reproducibility

### TC-17-INFRA-EXT-1.1 — The render libraries are present in the built image

| Field | Value |
|---|---|
| Description | The PDF renderer's dependencies are native, not Python. They can be present on a developer machine and absent from the built image, so export passes locally and answers `500` on every request in the deployed container. |
| Preconditions | The backend image is built fresh from `backend/Dockerfile` (no cached layer from a previous base image); containers belonging to other sessions are left alone. |
| Test data | Image `textery-backend:latest`; libs `libpango-1.0`, `libcairo`, `libgdk_pixbuf-2.0`; render probe rendering `<p>тест</p>` to `/tmp/probe.pdf` |
| Steps | 1. `docker run --rm textery-backend:latest ldconfig -p` and look for each of the three libraries.<br>2. `docker run --rm textery-backend:latest python -c "import weasyprint; weasyprint.HTML(string='<p>тест</p>').write_pdf('/tmp/probe.pdf')"`.<br>3. Read the probe's exit code and stderr. |
| Expected result | Step 1 lists all three libraries; step 2 exits `0` with empty stderr — no `OSError: cannot load library` and no missing-`.so` message, proving the libs are loadable and not merely installed — and the produced `/tmp/probe.pdf` starts with `%PDF-`. |
| Status | Not run |
