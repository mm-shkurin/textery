# Decision: Account persistence + Clock port introduced at Scenario 1.5

**Date**: 2026-07-14 **Scenarios**: 1.5

Scenario 1.5 requires a real created account (server-generated `id`, `is_verified=false`) — `RegisterUser` currently validates only and persists nothing.

| Rejected | Why |
|----------|-----|
| Hardcode `datetime.now(timezone.utc)` for `created_at` | Story-wide requirement mandates an injectable/mockable clock for TTL/cooldown logic landing in 2.x/4.x/5.x; deferring the port means retrofitting `RegisterUser` plus every later usecase's constructor. |
| Add `email` unique constraint now | Duplicate-email rejection semantics (2.2/2.4/2.4a) aren't designed yet; adding the constraint before that design risks a mismatch. Schema stays additive-safe: nullable/type choices made now must not force a destructive migration later. |
| Serialize the domain `Account` directly in the REST response | Would put `password_hash` on the same object returned to the client; a naive controller change could leak it. |

**Chosen**: domain `Account` entity + `AccountRepository` port + SQLAlchemy `accounts` table/migration (mirrors `Generation`/`generations` pattern), a `Clock` port + `SystemClock` adapter injected into `RegisterUser` for `created_at`, and a dedicated `RegisterResponseDto` (id, is_verified only).

## Model

- `backend/domain/src/auth/account.py`: `Account.create(id, email, password_hash, clock)` — pins `is_verified=False` internally, no public setter.
- `backend/usecase/src/auth/account_repository.py`: `AccountRepository` port — `save(account) -> None`.
- `backend/usecase/src/shared/clock.py` (or `auth/clock.py`): `Clock` port — `now() -> datetime`.
- `backend/adapters/db/src/model/auth/account_model.py` + `account_storage.py`: SQLAlchemy model/repo, mirrors `generation_model.py`/`generation_storage.py`.
- `backend/adapters/db/migrations/versions/*_accounts_table.py`: `id` (UUID pk), `email` (String, not null, no unique constraint yet), `password_hash` (String, not null), `is_verified` (Boolean, not null, default false), `created_at` (DateTime with timezone, not null).
- `backend/adapters/rest/src/dto/auth/register_response_dto.py`: `RegisterResponseDto` — `id`, `is_verified` only, built from the domain `Account`, never from the request DTO.
- `RegisterUser.execute` gains `AccountRepository` and `Clock` as injected ports; returns the persisted `Account`.

## Edge Cases

| Case | Behavior |
|------|----------|
| Request body includes `is_verified`/`id` | Dropped at `RegisterRequestDto` parse (pinned by an explicit `extra="ignore"` test); even if it reached the usecase, `Account.create` has no path to set `is_verified=True` or accept a caller-supplied `id`. |
| Persistence failure (DB down, constraint violation) | Maps to a defined exception (not a raw DB/SQLAlchemy error surfaced to the client). |
| Scenario 1.5 acceptance test re-run | Uses a per-run-unique email fixture (no DB cleanup exists yet), so repeated runs don't accumulate rows or collide once a uniqueness constraint lands in 2.2. |
| `password_hash` disclosure | Never present on `RegisterResponseDto`; asserted absent from the serialized response body. |
