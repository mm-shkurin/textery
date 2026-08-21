<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Infrastructure Tests (Extended)

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

## 1. Response Compatibility

### TC-18-INFRA-EXT-1.1 — An existing consumer tolerates the new response fields

| Field | Value |
|---|---|
| Description | `generation_id` and `title` are additive on `DocumentResponse`. A consumer built with a strict deserializer — one that errors on unknown properties — breaks the moment the new backend deploys, even though the change is "backwards compatible" on paper. |
| Preconditions | The pre-migration client build (`textery-backend:pre-generation-id`-era frontend / API consumer) is available; the new backend is running from `infra/docker-compose.yml` with ports from `infra/.env`; account A signed in; a converted document exists carrying non-null `generation_id` and a `title`. |
| Test data | Document from generation G1; response body carries `generation_id: "4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426"` and `title: "История Москвы"` — both unknown to the old consumer |
| Steps | 1. Point the pre-`generation_id` consumer at the new backend.<br>2. Have it call `GET /api/v1/documents/{document_id}` for that document.<br>3. Read the consumer's parse result, its rendered output, and its error log. |
| Expected result | The consumer parses the body without raising — no `UnrecognizedPropertyException` / unknown-key error of any kind in its log; it renders the document's `content` and `document_id` as before, silently ignoring `generation_id` and `title`; its exit status / request result is success, not a deserialization failure. |
| Status | Not run |

## 2. Migration Reversibility

### TC-18-INFRA-EXT-2.1 — The migration is reversible without data loss on manual documents

| Field | Value |
|---|---|
| Description | A downgrade path is the only way out of a bad deploy. If the rollback drops more than the column it added — or fails on rows written after the upgrade — a rollback becomes data loss on documents that predate the feature entirely. |
| Preconditions | A database seeded with document D0 (created before the migration, `generation_id` null) and at least one document created after the migration from generation G1 (`generation_id` non-null); the migration has been applied; no container from another session is touched. |
| Test data | Document D0 id `bd39c81a-5f27-4e64-90b8-7c2a4e150d63` with a recorded snapshot of its `content`, `title`, `version`, `created_at`, `updated_at`; post-migration document from generation G1; rollback command `alembic downgrade -1` |
| Steps | 1. Record the full row of document D0 and the row count of `documents`.<br>2. Run `alembic downgrade -1`.<br>3. Inspect the `documents` table schema.<br>4. Re-read document D0's row and the total row count.<br>5. Start the pre-migration image against the rolled-back schema and `GET /api/v1/documents/bd39c81a-5f27-4e64-90b8-7c2a4e150d63`. |
| Expected result | Step 2 exits `0` with no error; step 3 shows `generation_id` and its UNIQUE constraint gone and every other column unchanged; step 4 shows document D0's `content`, `title`, `version`, `created_at` and `updated_at` identical to the step-1 snapshot and the row count unchanged (post-migration documents survive too, minus only their link); step 5 answers `200 OK` with document D0's content — the old image runs against the rolled-back schema. |
| Status | Not run |
