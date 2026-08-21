<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Infrastructure Tests

Surfaces: the bundled document-font asset in both images, the `documents.page_settings`
JSONB column and its Alembic migration, and the rolling-deploy window in which an old and a
new application version both write the `documents` row.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Compose stack | `docker compose -f infra/docker-compose.yml` with services `postgres`, `backend`, `frontend` (ports read from `infra/.env`, never hardcoded) |
| Backend font asset | `backend/application/src/resources/fonts/LiberationSerif-Regular.ttf` inside the backend image |
| Frontend font asset | `frontend/public/fonts/LiberationSerif-Regular.ttf` in the built frontend bundle |
| Migration | `backend/adapters/db/migrations/versions/e7f8a9b0c1d2_documents_page_settings.py` (`alembic upgrade head` / `alembic downgrade -1`) |
| Account A | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери` |
| Previous application version | the last image tag built before `page_settings` entered `DocumentModel` |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Startup Validation

### TC-10-INFRA-1.1 — A missing document font fails the application at boot

| Field | Value |
|---|---|
| Description | This is the guard that keeps the font from failing *lazily*: without it, a misbuilt image serves successful exports laid out in a substitute face, which is a wrong document that looks like a right one. |
| Preconditions | The compose stack is down; a backend image is built with the font asset deleted, and a second one with the file present but `chmod 000`. |
| Test data | `backend/application/src/resources/fonts/LiberationSerif-Regular.ttf` removed, then made unreadable |
| Steps | 1. Start `backend` from the image with the font deleted and capture stdout/stderr and the exit code.<br>2. Poll the backend health endpoint for 30 s.<br>3. Repeat steps 1–2 with the unreadable-font image. |
| Expected result | In both runs the process exits non-zero during startup with a log line naming the missing asset by path (`LiberationSerif-Regular.ttf`) and the reason (missing / unreadable); the health endpoint never answers `200` — the container never reaches a serving state; no export request is ever accepted. |
| Status | Not run |

### TC-10-INFRA-1.2 — The render path depends on no system-installed face

| Field | Value |
|---|---|
| Description | A render that silently borrows a face installed on the build host produces documents that change when the base image changes. |
| Preconditions | A backend image built with the system font packages removed (`fc-list` reports only the bundled asset); the stack is up on that image. |
| Test data | Document A2 (settings `S1`, header `Кафедра ИВТ`), `format=pdf` |
| Steps | 1. `docker compose exec backend fc-list` and record the faces present.<br>2. Export document A2 as `pdf` with account A's token.<br>3. Read the PDF's embedded-font list. |
| Expected result | Step 1 lists Liberation Serif and no other document face. Step 2 answers `200 OK` with a valid PDF. Step 3 shows the text drawn in Liberation Serif only — no `DejaVu`, `Noto` or any other substituted family appears in the font list. |
| Status | Not run |

---

## 2. Database

### TC-10-INFRA-2.1 — The database being unavailable does not lose the user's page settings

| Field | Value |
|---|---|
| Description | A failure that both clears the panel and half-writes the row leaves the user with nothing to retry and a document in a state neither side chose. |
| Preconditions | Account A is in the editor on document A2 with new geometry entered in the page setup panel and not yet applied. |
| Test data | Entered values `A5`, margins 25/20/25/20, 12 pt, 1.2, header `Кафедра ИВТ`; `docker compose stop postgres` immediately before pressing `Применить` |
| Steps | 1. Enter the values in the panel.<br>2. `docker compose -f infra/docker-compose.yml stop postgres`.<br>3. Press `Применить` and record the HTTP response.<br>4. Read the panel fields.<br>5. `docker compose start postgres`, then read the `page_settings` column of document A2 directly. |
| Expected result | Step 3: `500` with body exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` and the `Не удалось сохранить параметры страницы` banner with `Повторить`. Step 4: all entered values are still in the fields. Step 5: the stored `page_settings` equals `S1` — the pre-request value, with no partial object and no `version` bump. |
| Status | Not run |

### TC-10-INFRA-2.2 — Page settings survive a database restart

| Field | Value |
|---|---|
| Description | Settings written into a connection that the pool later re-establishes must be on disk, not only in a session. |
| Preconditions | Document A2 saved with settings `S1` and the save confirmed `200 OK`. |
| Test data | Document A2 id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Steps | 1. `GET` document A2 and record `page_settings` and `version`.<br>2. `docker compose -f infra/docker-compose.yml restart postgres` and wait for the backend pool to reconnect.<br>3. `GET` document A2 again. |
| Expected result | Step 3 answers `200 OK` (no `500` from a stale pooled connection) and `page_settings` equals `S1` key for key, with the same `version` recorded in step 1. |
| Status | Not run |

---

## 3. Rolling Deploy

### TC-10-INFRA-3.1 — An old instance still serves documents after the column lands

| Field | Value |
|---|---|
| Description | The migration lands before every instance is replaced; an additive column that the old model cannot tolerate takes the whole fleet down mid-deploy. |
| Preconditions | `alembic upgrade head` has applied `e7f8a9b0c1d2`; one backend container runs the previous application version against the migrated database. |
| Test data | Document A2 (`page_settings` = `S1`) and document A1 (`page_settings` `NULL`), read through the old instance |
| Steps | 1. Apply the migration.<br>2. Start a backend container on the previous image against the same database.<br>3. `GET /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` through the old instance.<br>4. `GET` document A1 through the old instance. |
| Expected result | Both reads answer `200 OK` with the document's `content`, `version` and `updated_at`; no `500` and no error naming an unknown column; the old instance's response simply omits `page_settings`, which its contract never declared. |
| Status | Not run |

### TC-10-INFRA-3.2 — An old instance's save does not erase page settings

| Field | Value |
|---|---|
| Description | This is the half of the rolling-deploy story the read path does not cover: a full-row write from a model that has no such column is what silently drops the data. |
| Preconditions | Document A2 has `page_settings` = `S1`, written by the new version; an old-version backend instance is running against the same database. |
| Test data | Old-instance save body `{"content":"<p>Правка со старого инстанса.</p>","version":<current>}` |
| Steps | 1. Read the `page_settings` column of document A2 directly and hash the JSONB.<br>2. `PUT /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` through the OLD instance with the body above.<br>3. Re-read and re-hash the `page_settings` column. |
| Expected result | Step 2 answers `200 OK` and the content is updated. Step 3: the `page_settings` JSONB hash equals the step-1 hash byte for byte — the column is neither `NULL` nor a partially rewritten object. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the bundled document font asset` | The Liberation Serif webfont shipped in the image / frontend bundle |
| `startup fails` | Fail-fast at application boot, consistent with story 17's missing-render-lib rule |
| `the previous application version` | An application build without `page_settings` in its document model |
| `the sanctioned error` | Generic client-safe error body, no internals |
