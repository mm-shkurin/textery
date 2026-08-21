<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Generate → edit — Infrastructure Tests

Covers the schema evolution, the concurrency-closing constraint, and config drift for the
new conversion path.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Migration under test | the additive migration adding `documents.generation_id` (nullable uuid) with a UNIQUE constraint |
| Pre-migration image | `textery-backend:pre-generation-id` (the story-5 release) |
| Generation G1 | id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`, completed, owned by account A, `document_type` `доклад` |
| Existing document D0 | id `bd39c81a-5f27-4e64-90b8-7c2a4e150d63`, created before the migration, `generation_id` null |
| Compose file | `infra/docker-compose.yml`; ports read from `infra/.env`, never hardcoded |
| Fake provider | the deterministic CI generation provider (markdown output) |

---

## 1. Schema Migration

### TC-18-INFRA-1.1 — The generation_id column is additive and nullable

| Field | Value |
|---|---|
| Description | Every document that already exists was created without a generation; a non-nullable column or a renamed neighbour makes the migration unrunnable on real data. |
| Preconditions | The database holds pre-migration document rows, including D0; the schema is captured before the migration. |
| Test data | Document D0; the pre- and post-migration `\d documents` output |
| Steps | 1. Capture the `documents` table definition before the migration.<br>2. Apply the migration.<br>3. Capture the definition again and diff it.<br>4. `SELECT generation_id FROM documents WHERE id = 'bd39c81a-5f27-4e64-90b8-7c2a4e150d63'`. |
| Expected result | The migration applies without error on populated data; the diff shows `generation_id uuid NULL` added and nothing else removed or renamed; D0's `generation_id` is `NULL` and the row is still valid and readable. |
| Status | Not run |

### TC-18-INFRA-1.2 — Old code survives the new column during a rolling deploy

| Field | Value |
|---|---|
| Description | During a rolling deploy the migrated schema is served by the previous release for minutes; if old code cannot insert against the new column, the deploy takes the fleet down midway. |
| Preconditions | The database is migrated; the pre-migration image is available and pointed at it. |
| Test data | Pre-migration image `textery-backend:pre-generation-id`; a manual create `POST /api/v1/documents` with `{"document_type": "доклад"}`; document D0 for the read |
| Steps | 1. Apply the migration.<br>2. Start the pre-migration image against the migrated database.<br>3. `POST /api/v1/documents` with account A's token.<br>4. `GET /api/v1/documents/bd39c81a-5f27-4e64-90b8-7c2a4e150d63` and `GET /api/v1/documents`.<br>5. Read the container log. |
| Expected result | Steps 3 and 4 answer `2xx`; the inserted row carries `generation_id = NULL`; the listing returns without error and old consumers tolerate the additive `generation_id` and `title` fields; the log holds no error from either operation. |
| Status | Not run |

---

## 2. Concurrency Constraint

### TC-18-INFRA-2.1 — A unique constraint on generation_id rejects a second document

| Field | Value |
|---|---|
| Description | This constraint is the single guard that closes idempotency, the concurrent race and the client double-fire. If it is missing at the storage level, every application-level check is a check-then-insert with a window. |
| Preconditions | A document already exists linked to generation G1; the migration is applied. |
| Test data | Direct SQL insert of a second `documents` row with `generation_id = '4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426'`, bypassing the application entirely |
| Steps | 1. Convert G1 through the API so one linked document exists.<br>2. `INSERT` a second document row with the same `generation_id` directly against the database.<br>3. Read the error and re-count rows for that `generation_id`.<br>4. `INSERT` two rows with `generation_id = NULL`. |
| Expected result | Step 2 is rejected by the database with a unique-violation error naming the `generation_id` constraint; exactly one row carries that `generation_id`; step 4 succeeds — the constraint permits multiple NULLs, so manual documents are unaffected. |
| Status | Not run |

---

## 3. Referential Integrity

### TC-18-INFRA-3.1 — The generation link has a defined on-delete policy

| Field | Value |
|---|---|
| Description | An undefined policy either blocks generation cleanup forever or leaves documents pointing at rows that no longer exist — and the user's document must never disappear because its source generation was purged. |
| Preconditions | Generation G1 converted into a document; the foreign key definition is readable from the schema. |
| Test data | The `documents.generation_id` foreign key and its declared `ON DELETE` action; generation G1 and its linked document |
| Steps | 1. Read the foreign-key definition and its `ON DELETE` clause from the schema.<br>2. Delete generation G1 at the storage level.<br>3. Read the linked document row and `GET /api/v1/documents/{document_id}`. |
| Expected result | The foreign key declares an explicit `ON DELETE` action (not the implicit default); after step 2 the behaviour matches that declaration — the delete is refused, or the document survives with `generation_id` set to `NULL`; in no case is a document left referencing a deleted generation, and step 3 still answers `200` if the document was meant to survive. |
| Status | Not run |

---

## 4. Config & Dependency

### TC-18-INFRA-4.1 — The conversion path is pinned against the production provider output shape

| Field | Value |
|---|---|
| Description | The CI fake emits markdown; production GigaChat output is unverified and may be plain text. A conversion tested only against the fake passes CI and produces a one-blob document in production. |
| Preconditions | A captured sample of the production provider's actual response shape is stored as a fixture, alongside the fake provider's markdown fixture. |
| Test data | Production-shaped fixture (plain text with blank-line paragraphs, no `#` headings); fake-provider fixture (`## Введение` markdown) |
| Steps | 1. Convert a generation carrying the production-shaped fixture.<br>2. Read the stored content.<br>3. Convert a generation carrying the fake's markdown fixture and read that content.<br>4. Remove the production-shaped fixture from the suite and re-run. |
| Expected result | Step 1 answers `201` with valid sanitized HTML — paragraphs preserved, no raw markdown characters left visible, nothing empty; step 3 also answers `201`; step 4 makes the suite fail, proving the production shape is actually exercised and not only the fake's format. |
| Status | Not run |

### TC-18-INFRA-4.2 — The markdown dependency passes the vulnerability audit

| Field | Value |
|---|---|
| Description | The markdown parser runs on untrusted model output, so a known CVE in it is directly reachable by anything the model can be persuaded to write. |
| Preconditions | The backend lockfile carries the markdown-parser dependency at a pinned version. |
| Test data | The CI `audit` job (`pip-audit`) over the backend lockfile |
| Steps | 1. Run the CI dependency-audit job against the current lockfile.<br>2. Read its report and exit code.<br>3. Temporarily pin a known-vulnerable version of the markdown parser and re-run. |
| Expected result | Step 2 exits `0` with zero reported vulnerabilities for the markdown parser and its transitive tree; step 3 exits non-zero naming that dependency, proving the gate is live rather than merely green. |
| Status | Not run |
