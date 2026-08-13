# Profile management (view + rename)

## Brief Description

A signed-in user opens their profile from the avatar menu, sees the address they registered
with and when, and can set or clear a display name. The header stops decoding the JWT and
reads the same endpoint.

## Flow

1. A signed-in user opens the avatar menu and clicks «Мой профиль».
2. The app navigates to `/profile`.
3. The screen requests `GET /api/v1/auth/me` with the Bearer access token.
4. It renders `email`, registration date (`created_at`), and a name field — empty when the
   account has never had a name.
5. The user types a name and saves → `PATCH /api/v1/auth/me` with `{ "name": ... }`.
6. On 200 the screen and every mounted header show the new name; avatar initials recompute
   from it.
7. Clearing the field and saving stores NULL; display falls back to the email and to
   email-derived initials.
8. A validation failure renders an inline message; the field keeps what the user typed.
9. An expired/invalid token takes the existing session-expired path.

## Acceptance Criteria

- «Мой профиль» sits in the avatar menu above «Выйти» and routes to `/profile`.
- `/profile` shows the caller's own email, registration date, and current name.
- Saving a name persists it: a re-read **in a separate DB session** returns the new value.
- Saving a blank value clears the name (NULL, 200); screen and header fall back to email
  and email-derived initials.
- After a successful save, every mounted header shows the new name with no page reload, and
  an in-app navigation away and back still shows it without a second `/me` being required.
- Signing out and signing in as another account in the same tab shows the second account's
  identity — never the first account's cached name or email, including when the first
  account's `/me` was still in flight across the switch.
- A name over the bound is refused 400 with the canonical body; nothing is persisted.
- `GET`/`PATCH /me` without a valid access token answer 401.
- A caller can never read or write another account's profile, and a rename leaves every
  other account's row byte-identical.
- The header renders its page — with a defined identity — when `/me` is slow, failing,
  unauthorized, or answers 200 with a malformed body. «Выйти» works in every one of those.

The full folded guard set is in `13_ProfileManagement_AcceptanceCriteria.md`.

## Validation Rules

| Field | Rule |
|-------|------|
| `name` (raw request value) | refused **before** trim/NFC when over 256 code points, with its own `error_code` distinct from the normalized-bound refusal |
| `name` (normalized) | trim + NFC, then 1–60 **code points**; the client counter counts the same unit |
| `name` — blankness | blank = no visible characters after stripping Unicode whitespace **and category `Cf`** (reuses `Generation._is_blank_topic`'s definition); a blank value clears the name to NULL, so "no name" has exactly one stored representation |
| `name` — field presence | absent key → name unchanged (fail closed); explicit `null` → clears, same as blank; the request model must carry presence, not collapse all three to `None` |
| request body | bounded at the transport boundary; an oversized body is refused without being fully buffered and parsed |
| Authorization header | Bearer access token required; missing, expired, refresh-typed, or unknown-typed → 401; a valid token whose account row is gone → the identical 401 |

## Screen States

- Profile — loading (`/me` in flight), a defined placeholder, not a blank avatar that pops.
- Profile — loaded, name set.
- Profile — loaded, name never set (field empty, email shown as identity).
- Profile — saving (submit non-interactive until the response returns).
- Profile — inline validation error.
- Profile — load failed: a message plus a retry affordance, not a perpetual spinner.
- Avatar menu with «Мой профиль» added.
- Header — degraded identity, visibly distinct from the loading placeholder.

## Core Requirements

- New nullable `name` column on `accounts` via migration; no backfill.
- `GET /api/v1/auth/me` returns `email`, `name`, `created_at` only — no `is_verified`. The
  `name` key is always present, `null` when unset. `created_at` serializes as a `Z`-suffixed
  UTC instant, matching every other timestamp on this project's wire.
- `PATCH /api/v1/auth/me` binds **`name` only** through a purpose-built request DTO — never
  the `/me` response DTO reused for write.
- The rename emits an UPDATE that sets **only** `name`; it must not rewrite `email`,
  `password_hash`, `is_verified`, `created_at`, or `failed_attempt_count`.
- Concurrent renames are **last-write-wins** by decision, not by omission — there is no
  version column and no 409.
- Both routes resolve the account through the existing `get_current_owner_id`; the account
  identifier is never a route or body parameter.
- A domain value object owns the name rules, modelled on `Email`/`GeneratedTitle`, and
  raises into the canonical `{error_code, message}` 400 — never a bare `ValueError` that
  reaches the 500 handler.
- Both routes answer `Cache-Control: no-store` — the body is account-specific.
- The write path must update `save()`'s update branch, `AccountModel.from_domain`, and
  `to_domain`; all three enumerate columns by hand, and the fakes cannot see an omission.
- The rename usecase is wired to a real `SqlAlchemyUnitOfWork` bound to the repository's
  session, and commits exactly once on success, never on rejection.
- The frontend drops `accountEmailFromToken` / `currentAccountEmail`; `useAccountEmail` is
  reworked onto `/me` while keeping its session-change reactivity.
- The identity snapshot is stamped with a session generation: a response from a superseded
  generation is dropped, the snapshot is updated on the write path, and it is cleared on
  sign-out.
- One `/me` request per page — shared across both mounted `ProfileMenu` instances and
  across in-app navigation — with a bounded timeout, abort on unmount, and capped,
  jittered retries.
- `accountInitials` stays, deriving from the name when set and the email otherwise, and
  must never split a grapheme or emit a lone surrogate.
- The profile form reuses the existing `useUnsavedGuard` for typed-but-unsaved input.
