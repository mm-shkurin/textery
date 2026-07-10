# Task 2: Generation flow hardening

Type: refactoring

## Solution

Triggered by a targeted code review of the generation flow (provider auth,
error surfacing, storage concurrency, domain constants/typing/input limits).
Six independent fixes, each landed as its own commit:

1. **Fail-fast GigaChat credentials** — `GigaChatProvider.__init__` now
   raises `ConfigurationException` when `GIGACHAT_CREDENTIALS` is unset or
   blank, instead of silently sending `Authorization: Basic None` to the
   provider.
2. **Sanitize `error_message`** — `GenerateDocument.execute` no longer
   stores the raw provider exception text (which could leak upstream URLs
   or infra details) in `error_message`. It now stores a generic
   `GENERIC_FAILURE_MESSAGE` and keeps the full error in the server log only.
3. **Dedup status constants** — `GenerationModel.ALLOWED_STATUSES` and its
   `CheckConstraint` SQL are now built from `generation.py`'s
   `PENDING_STATUS` / `IN_PROGRESS_STATUS` / `COMPLETED_STATUS` /
   `FAILED_STATUS` constants instead of re-declaring the strings.
4. **Typing consistency** — `generate_document.py`'s `ProviderError | None`
   changed to `Optional[ProviderError]` to match the `Optional[X]` style
   used everywhere else in the backend.
5. **Length guards** — `Generation.create()` rejects `topic` over 500 chars,
   `requirements`/`extra_wishes` over 2000 chars each, before the input ever
   reaches the external LLM. Caps are provisional (no stated product limit
   found) — revisit if the spec states different numbers.
6. **Optimistic locking** — `generations` gained a `version` column
   (migration `b2c3d4e5f6a7`, chained under `a1b2c3d4e5f6`). Storage
   `update()` compares the version and raises `ConflictException` on a
   stale write instead of silently last-write-winning a concurrent status
   transition.

## Key Files

- backend/adapters/generation_provider/src/provider/gigachat_provider.py
- backend/adapters/generation_provider/tests/provider/test_gigachat_provider.py
- backend/usecase/src/generation/generate_document.py
- backend/usecase/tests/generation/test_generation_lifecycle_usecase.py
- backend/usecase/tests/statements/generation_lifecycle_statements.py
- backend/adapters/db/src/model/generation/generation_model.py
- backend/adapters/db/src/access/generation/generation_storage.py
- backend/adapters/db/tests/access/generation/test_generation_storage.py
- backend/adapters/db/tests/statements/generation_storage_statements.py
- backend/adapters/db/migrations/versions/b2c3d4e5f6a7_add_version_column.py
- backend/domain/src/generation/generation.py
- backend/domain/src/shared/exceptions.py
- backend/domain/tests/generation/test_generation.py (new test suite for this module)
