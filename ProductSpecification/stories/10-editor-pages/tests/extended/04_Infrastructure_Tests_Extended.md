> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Infrastructure Tests (Extended)

Surfaces: the bundled font asset in both deployed artifacts, the `documents.page_settings`
migration, and the boot-time configuration the render and pagination paths depend on.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Compose stack | `docker compose -f infra/docker-compose.yml` with services `postgres`, `backend`, `frontend` (ports read from `infra/.env`, never hardcoded) |
| Backend font asset | `backend/application/src/resources/fonts/LiberationSerif-Regular.ttf` inside the backend image |
| Frontend font asset | `frontend/public/fonts/LiberationSerif-Regular.ttf` in the built frontend bundle |
| Migration | `backend/adapters/db/migrations/versions/e7f8a9b0c1d2_documents_page_settings.py` |
| Migration commands | `alembic upgrade head` / `alembic downgrade -1`, run inside the `backend` service |
| Account A | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Budget config | `PAGINATION_BUDGET_MS` (2000) and `RENDER_DEADLINE_SECONDS` (30) in the backend environment |
| Locale config | the application's pinned invariant formatting locale, independent of the container's `LC_ALL` |

## 1. Font Asset

### TC-10-INFRA-1.1 — A corrupted font asset fails at boot, not at first render

| Field | Value |
|---|---|
| Description | A present-but-unparseable file passes an existence check and fails only inside the render, where the library substitutes a face and returns a wrong document with a `200`. |
| Preconditions | The stack is down; a backend image is built with the font file truncated to its first 512 bytes, and a second one with 1 KB of random bytes in its place. |
| Test data | `LiberationSerif-Regular.ttf` truncated to 512 bytes; then replaced with random bytes |
| Steps | 1. Start `backend` from the truncated-font image; capture the log and the exit code.<br>2. Poll the health endpoint for 30 s and attempt one export.<br>3. Repeat with the random-bytes image. |
| Expected result | In both runs startup fails non-zero with a log line naming `LiberationSerif-Regular.ttf` and the reason (unparseable / invalid font), and the validation is a real parse rather than a file-exists check; the health endpoint never answers `200`; the attempted export gets no response because the service never served — zero exports are produced against the corrupt asset. |
| Status | Not run |

### TC-10-INFRA-1.2 — The frontend and the renderer carry the same font file

| Field | Value |
|---|---|
| Description | A drift between the two is invisible in every functional test and quietly breaks the one property the shared font exists to provide — that the editor and the PDF measure text the same way. |
| Preconditions | Both images are built from the current commit and are running. |
| Test data | `sha256` of the font file extracted from each artifact |
| Steps | 1. `docker compose -f infra/docker-compose.yml exec backend sha256sum /app/resources/fonts/LiberationSerif-Regular.ttf`.<br>2. `docker compose -f infra/docker-compose.yml exec frontend sha256sum /usr/share/nginx/html/fonts/LiberationSerif-Regular.ttf`.<br>3. Compare the two digests and the two file sizes. |
| Expected result | The two `sha256` digests are identical and the byte sizes match; the asset is the same file in both artifacts, not two builds of the same family. |
| Status | Not run |

---

## 2. Migration

### TC-10-INFRA-2.1 — The migration is reversible without touching document content

| Field | Value |
|---|---|
| Description | A rollback that rewrites the `documents` table risks the data the column was never supposed to touch; the down-migration must drop the column and nothing else. |
| Preconditions | A database with at least 20 documents at known `content` and `version`; `alembic upgrade head` has applied `e7f8a9b0c1d2`. |
| Test data | Per-row `sha256` of `content` and the `version` and `updated_at` values, captured before the rollback |
| Steps | 1. Hash every document's `content` and record its `version` and `updated_at`.<br>2. Run `alembic downgrade -1` inside the `backend` service.<br>3. Re-hash and re-read every row.<br>4. Confirm the column is gone from `information_schema.columns`. |
| Expected result | The downgrade completes without error; every row's `content` hash, `version` and `updated_at` are unchanged; `page_settings` is absent from `information_schema.columns` for `documents`; the row count is unchanged. |
| Status | Not run |

### TC-10-INFRA-2.2 — The migration does not rewrite existing rows

| Field | Value |
|---|---|
| Description | An additive column with a server-side default rewrites every row and takes a table lock proportional to the table — and materializes a preset into documents that never chose one. |
| Preconditions | A database at the revision before `e7f8a9b0c1d2`, holding 10 000 documents. |
| Test data | `pg_stat_user_tables.n_tup_upd` for `documents` before and after; `xmin` of a sample of 50 rows before and after |
| Steps | 1. Record `n_tup_upd` for `documents` and the `xmin` of 50 sampled rows.<br>2. Run `alembic upgrade head`.<br>3. Re-read `n_tup_upd` and the same rows' `xmin`.<br>4. `SELECT count(*) FROM documents WHERE page_settings IS NOT NULL`.<br>5. `GET` one of those documents through the API. |
| Expected result | `n_tup_upd` is unchanged and every sampled `xmin` is unchanged — no row was written. Step 4 returns `0`: every pre-existing row holds SQL `NULL`. Step 5 answers `200 OK` with `page_settings: null`, not a materialized preset object. |
| Status | Not run |

---

## 3. Configuration

### TC-10-INFRA-3.1 — An unset pagination or render budget fails fast

| Field | Value |
|---|---|
| Description | A budget silently defaulted at the first request means the deployed timeout is whatever the code happens to hardcode, and nobody learns it was never configured. |
| Preconditions | The stack is down; the backend can be started with individual environment variables removed. |
| Test data | Start once with `PAGINATION_BUDGET_MS` unset, once with `RENDER_DEADLINE_SECONDS` unset, once with both unset |
| Steps | 1. Start `backend` with `PAGINATION_BUDGET_MS` removed; capture the log and exit code.<br>2. Poll the health endpoint for 30 s.<br>3. Repeat for `RENDER_DEADLINE_SECONDS` and for both together. |
| Expected result | Every run exits non-zero at startup with a log line naming the missing variable exactly (`PAGINATION_BUDGET_MS` / `RENDER_DEADLINE_SECONDS`); the health endpoint never answers `200`; no request is ever served against a silently defaulted budget. |
| Status | Not run |

### TC-10-INFRA-3.2 — The render locale is pinned rather than inherited

| Field | Value |
|---|---|
| Description | If the render path reads the ambient locale, a base-image change alone can turn every geometry number into a comma-decimal string that the stylesheet drops. |
| Preconditions | Document A2 exists with fractional geometry (`line_height` 1.15, margins 20.5/15.25/20.5/30.75, 11.5 pt); a reference PDF exported under `LC_ALL=C.UTF-8` is stored. |
| Test data | Container started with `LC_ALL=ru_RU.UTF-8` and `LC_NUMERIC=ru_RU.UTF-8` |
| Steps | 1. Start the backend with the comma-decimal ambient locale and confirm it inside the container (`locale`).<br>2. Export document A2 as `pdf` and as `docx`.<br>3. Capture the stylesheet handed to the PDF renderer.<br>4. Compare both files' geometry with the `C.UTF-8` reference. |
| Expected result | Step 1 shows the ambient locale is indeed comma-decimal. Step 3: every number in the stylesheet uses `.` (`line-height: 1.15`, `margin-left: 30.75mm`) — no `1,15` appears and no declaration is missing. Step 4: `/MediaBox`, page count, text-frame geometry and the DOCX `w:pgSz`/`w:pgMar`/`w:spacing` values are identical to the reference. |
| Status | Not run |
