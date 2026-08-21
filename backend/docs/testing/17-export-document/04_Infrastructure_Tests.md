<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Export document — Infrastructure Tests

Native render dependencies, config fail-fast, resource release, and the shared schema
change.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике` |
| Image under test | the backend image built from `backend/Dockerfile` |
| Native render libs | `libpango-1.0`, `libcairo`, `libgdk_pixbuf-2.0` (WeasyPrint's system dependencies) |
| Render-timeout config | `EXPORT_RENDER_TIMEOUT_SECONDS` (default `30`) |
| Health check | `GET /health` on the backend container |
| Compose file | `infra/docker-compose.yml`; ports read from `infra/.env`, never hardcoded |

## 1. Render Dependencies

### TC-17-INFRA-1.1 — Missing native render libraries fail fast at boot

| Field | Value |
|---|---|
| Description | A pure `pip install` of WeasyPrint boots fine and then throws on the first export. The failure must surface at deploy time as a container that never goes healthy, not as a user's `500`. |
| Preconditions | A backend image built without the native render libraries (the apt install removed from the build stage). |
| Test data | Image tag `textery-backend:no-native-libs`; absent libs `libpango-1.0`, `libcairo`, `libgdk_pixbuf-2.0` |
| Steps | 1. Start a container from `textery-backend:no-native-libs`.<br>2. Read `docker ps` and the container log.<br>3. Call the health check.<br>4. If the process is still up, call `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=pdf`. |
| Expected result | The process exits non-zero at startup, or the health check answers non-`200`; the log names the missing library (e.g. `libpango`); the container never reaches a healthy state; the first export is not where the failure is discovered. |
| Status | Not run |

### TC-17-INFRA-1.2 — An unset render-timeout config fails fast at boot

| Field | Value |
|---|---|
| Description | An unset deadline means "render forever": one pathological document then holds a worker indefinitely and nothing in the request path notices. |
| Preconditions | The backend image is intact; the render-timeout variable is removed from the environment. |
| Test data | `EXPORT_RENDER_TIMEOUT_SECONDS` unset; then `abc`; then `30` |
| Steps | 1. Start the backend with the variable unset; read the log and exit code.<br>2. Start it with the variable set to `abc`.<br>3. Start it with the variable set to `30`. |
| Expected result | Steps 1 and 2 exit non-zero at startup with a log line naming `EXPORT_RENDER_TIMEOUT_SECONDS`; the process never begins serving with an unbounded render; step 3 starts normally and the health check answers `200`. |
| Status | Not run |

### TC-17-INFRA-1.3 — The render dependencies pass the vulnerability audit

| Field | Value |
|---|---|
| Description | The export path pulls a large new native-backed dependency tree; a known CVE in it must break the build rather than ship. |
| Preconditions | The lockfile carries the render dependencies (WeasyPrint and the DOCX writer) at pinned versions. |
| Test data | The CI `audit` job (`pip-audit`) over the backend lockfile |
| Steps | 1. Run the CI dependency-audit job against the current lockfile.<br>2. Read its report and exit code.<br>3. Temporarily pin a known-vulnerable version of one render dependency and re-run. |
| Expected result | Step 2 exits `0` with zero reported vulnerabilities across the render dependencies and their transitive tree; step 3 exits non-zero naming that dependency, proving the gate is live rather than merely green. |
| Status | Not run |

## 2. Resource Release

### TC-17-INFRA-2.1 — Repeated exports including failures do not leak resources

| Field | Value |
|---|---|
| Description | Native render handles freed only on the happy path leak once per failure; the instance then dies hours after deploy with no failing request to point at. |
| Preconditions | One backend instance; document A1 (renders fine) and document A8 (induced render failure) both exist; RSS, thread count and open file descriptors sampled every 10 s. |
| Test data | Document A8 id `e0b4f271-3a55-4d0c-b7ef-1a9c62d4b807`; 500 exports run serially at 9 successes to 1 induced failure; drift ceiling ±10 % of baseline after a 60 s settle |
| Steps | 1. Record baseline RSS, thread count and open FD count.<br>2. Run the 500-export sequence.<br>3. Wait 60 s to settle, then record the three metrics again.<br>4. Plot the samples and inspect the trend across the run. |
| Expected result | Post-run RSS, thread count and open FDs are all within ±10 % of baseline; the samples show no monotonic upward trend across the run; the process did not restart; the failure path releases as much as the success path. |
| Status | Not run |

## 3. Schema

### TC-17-INFRA-3.1 — Old code serves documents after the title column lands

| Field | Value |
|---|---|
| Description | During a rolling deploy the migrated schema is served by the previous release for minutes; an additive column the old code cannot tolerate takes the fleet down mid-deploy. |
| Preconditions | The database is migrated to include the additive `title` column on `documents`; the pre-migration application image is available. |
| Test data | Pre-migration image tag `textery-backend:pre-title`; document A1; rows both with `title = Отчёт по практике` and with `title = NULL` |
| Steps | 1. Apply the migration that adds `title`.<br>2. Start the pre-migration image against the migrated database.<br>3. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913` with account A's token.<br>4. `GET /api/v1/documents` for account A.<br>5. Save a document through the old code. |
| Expected result | Steps 3–5 all answer `2xx` with no error in the container log; the bodies carry the pre-migration field set; the migration renamed and dropped no existing column; rows with `title = NULL` are served like any other. |
| Status | Not run |
