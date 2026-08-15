# Profile management — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/auth/me | The caller's own profile: `email`, `name`, `created_at`. Read by the profile screen **and** by the header on every authenticated page. |
| PATCH | /api/v1/auth/me | Set or clear the display name. `name` only. |

Contracts: `api-specs/auth_me_get.yaml`, `api-specs/auth_me_update.yaml`.
The app-wide request-body cap this story introduces is in `api-specs/README.md`
§ Request Body Cap, because it applies to every endpoint, not only these two.

**Two operations on one path, not two paths.** No `/auth/profile` alongside `/auth/me`,
no separate `POST /auth/me/name`, and no re-`GET` after a rename — PATCH answers with the
full profile, so the client updates its identity snapshot from the response it already has.

## Decisions this step had to make

The interview named four edges and left them here by name (`interview.md`, Business Rules:
absent vs `null` vs `""`; whitespace and invisible characters; the `error_code` for
over-length; which body shapes answer Pydantic's 422 instead of the canonical 400). All
four are decided below. Nothing here is left for `/test-spec` to invent.

**Two error codes for length, not one.** `NAME_INPUT_TOO_LARGE` for a raw value over 256
code points, refused before trim/NFC; `INVALID_NAME` for a normalized value over 60. The
acceptance criteria require the two refusals to be distinguishable, and the reason is
written in the code they are modelled on: `Email` raises the identical message at both
stages, so no test there can prove the cheap gate ran at all. Names that read differently
at a glance were chosen over `NAME_TOO_LONG`/`INVALID_NAME`, which are both plausibly "the
name is too long" in a client's `switch`.

**A non-string `name` is refused by the domain, not by Pydantic.** `{"name": 123}` must
answer `400 {error_code, message}` — so the request DTO types the field permissively
enough to let the value reach the value object, rather than letting FastAPI's
`RequestValidationError` produce a 422 in a different envelope that **echoes the rejected
input back**. Same reason the over-length case must reach the domain path.

**Residual, named rather than silently accepted:** a body that is not valid JSON at all
(`{`, empty body, `text/plain`) still answers FastAPI's 422 in its own `{"detail": …}`
shape. Closing that means an app-wide `RequestValidationError` handler, which changes the
error contract of all 19 existing endpoints — `documents_save.yaml` already documents a 422
in the canonical `Error` shape that FastAPI does not actually produce, so the mismatch
predates this story and is wider than it. This story does not change it.
**ACTION (`/test-spec`):** assert the canonical envelope for non-string and over-length
`name`, and pin the malformed-JSON case as the one shape this contract does not own.

**The tri-state is the contract, before there is a second field to protect.** OMITTED
leaves the name untouched, explicit `null` clears, and a blank string clears identically.
It reads as over-engineering while `name` is the only writable field and becomes
destructive the moment story 8 or story 14 adds a second one — retrofitting presence after
a client is already sending `{}` is far more expensive than establishing it now.

**Blank is a stricter predicate than the topic's, and it is a new shared helper.** The
starting point is `required_topic()` in `backend/domain/src/generation/generation_validation.py`
— whitespace *and* category `Cf`. That is not enough for a name, in two ways that the first
draft of this file got wrong by reusing it verbatim:

- **`Cc` and `Cs` are refused outright** (`INVALID_NAME`), not stripped. A name of a single
  U+0000 (NUL) passes a whitespace+`Cf` filter, is under both length bounds, and is rejected by
  Postgres's `text` type — turning a documented 400 into a **500**. This is already recorded
  against the topic predicate as `.memory-bank/tasks/known-debt.md` #8; it arrives here as a
  contract bug rather than a debt item, because this route's spec claims 200-or-400 and
  nothing else.
- **Invisible-but-not-`Cf` characters are stripped for the blank test** — U+115F, U+1160,
  U+3164, U+FFA0 (Hangul fillers, `Lo`), U+2800 (Braille blank, `So`), U+17B4/U+17B5 (Khmer
  inherent vowels). All render as nothing and none are whitespace or `Cf`, so under the
  borrowed predicate a name of U+3164 persists and produces exactly the blank identity the
  rule exists to prevent — an outcome worse than leaving the rule out, because the contract
  claims it cannot happen. The acceptance criteria list only U+200B/U+FEFF/U+00A0, all three
  of which the borrowed predicate already caught, so no test would have gone red on this.

The point of the rule is unchanged: a set-but-unrenderable name defeats the NULL-keyed email
fallback and truncates the avatar's `aria-label` to «Меню профиля: », destroying the one job
that row has. Adopting the stricter helper for topics too would close known-debt #8 — story
1's call, not this story's.

**No `maxLength` in either schema.** OpenAPI counts UTF-16 units, the domain counts code
points, and they split at exactly the astral boundary the tests assert (`project_query.py`
carries the scar). A generated client trusting `maxLength: 60` would refuse a 60-emoji name
the server accepts.

**PATCH returns the full profile, and it is the normalized value, not an echo.** An NFD
request comes back canonically equivalent but not byte-equal; a trailing space comes back
trimmed. The client must recompute its dirty flag against the response, or a name with a
trailing space stays "unsaved" forever after a successful save.

**No 409, no version, no `If-Match`.** Last-write-wins is the decision. Because clearing is
first-class, a stale tab can *undo* a rename rather than merely overwrite it — accepted for
a display name, and written down so it is not read as a missed hazard.

**A `/me` failure is not a sign-out.** The header fires this call on every authenticated
page view, including at app boot before the user touches anything. The only authenticated
client, `frontend/src/features/auth/api/authorizedRequest.ts`, answers a 401 by renewing —
and `performRenewal`'s catch ends the session on *any* renewal failure, by design: "a 500,
the network being down". Before this story that path was only entered when a user did
something. After it, a blip during a rolling deploy, landing on the boot-time `/me` of every
open tab at a moment when the 15-minute access token happens to be expired, becomes a mass
sign-out plus the loss of typed-but-unsaved editor content. So: **a failing `GET /me` must
never reach `clearSession()`** — not a 5xx, not a timeout, not a 401 whose renewal then
fails. The header shows its degraded identity and the session stays whatever it was; only a
user-initiated request may conclude the session is dead. Two layers would otherwise resolve
this differently — the interceptor's job is to end dead sessions, the header's job is to
show nothing on failure — and the contract has to say which one owns a `/me` 401.
**ACTION (`/test-spec`):** a case per failure mode asserting the stored session survives.

**`GET /me` costs two pool connections per request, not one — and that is an open
decision.** The first draft asserted the opposite, that `session.get` hits a request-scoped
identity map so `/me` adds no second SELECT. It does not: `request_scoped`
(`backend/application/src/app/container/runtime.py`) opens **one session per dependency**,
and `create_account_existence` is itself `@request_scoped`, so `get_current_owner_id`'s
existence check and the profile read run on different sessions with different identity maps.
Two SELECTs, two simultaneous checkouts, two `pool_pre_ping` round-trips, against a pool of
5 + 10 overflow per process — on what this story makes the product's highest-rate endpoint,
sharing its queue with documents and generations. Sharing one session across a request's
dependencies would fix it and touches all thirteen factories, so it is an ADR
(`/architecture`) before the backend scenarios, not a decision this file can take. What this
file does fix is the false premise: the load scenario is sized against two connections, and
a SQL-capture guard (the `before_cursor_execute` idiom in `test_generation_storage_cas_shape.py`)
pins the count so it cannot drift silently either way.

**A missing account is 401, never 404.** No route on this story takes an account
identifier, so there is nothing to enumerate and no ownership check to get wrong; a
structurally valid token whose row is gone gets the same refusal as a forged one.

## Constants pinned here

| Constant | Value | Why |
|----------|-------|-----|
| Raw `name` cap | 256 code points | Cheap pre-normalization gate, per `Email`/`Password`. Generous on purpose: NFD is longer than NFC and must not be cut off before it is normalized. |
| Normalized `name` bound | ≤ 60 code points, **no lower bound** | Code points, like story 12's `q` and story 7's password length — never bytes, never UTF-16 units. A bound written "1..60" is dead text and worse than dead: every value normalizing to length 0 is blank and clears with 200, so a test author reading a lower bound writes `{"name": ""}` → 400, the opposite of the tri-state rule. |
| Request body cap (app) | 2 MiB | Fixed by the largest legitimate body in the product, not by this route: `documents_save` allows 200 000 code points, up to ~800 KB as UTF-8 before JSON escaping. |
| Request body cap (nginx) | 4 MiB, **above** the app cap | `infra/docker/nginx/frontend.conf` proxies `/api/` — every browser request crosses it. Unset today, so its 1 MiB default is the real ceiling and it answers with HTML, not `{error_code, message}`. Set below or equal to the app cap and the canonical 413 is unreachable for real users. See `api-specs/README.md`. |
| `Cache-Control` | `no-store`, both routes, **every response** | The body carries the account's email. Set at the route before the outcome is known, so 401 and 500 carry it too — otherwise a test written from the acceptance criteria and one written from the YAML disagree. |
| Concurrency control | none (last-write-wins) | A display name; a lost update costs one retype. |

## Not decided here

**One pool connection per `GET /me`, or two.** Measured as two (above). Fixing it means
sharing one session across a request's dependencies, which touches all thirteen
`@request_scoped` factories — an ADR via `/architecture`, due before the backend scenarios.
Until then the load scenario is sized against two, and the SELECT count is pinned by a test
so neither number is an assumption.

**The write path has no failure screen.** All eight mockups cover reading plus one
client-side validation, so the 5xx and network-drop states of `PATCH` are contract-only.
Already recorded as an ACTION on `13_ProfileManagement.md` § Screen States, due before
`/test-spec`; this file gives that state its API side (413/500 in the canonical envelope,
nothing persisted, the typed value still the client's to keep).

## Corrected after the review passes

The first version of this contract shipped four wrong statements, all caught by the
`agent-review` / `premortem` passes over commit `0c759887` and all corrected above. Kept
here because each one is a trap a reader could re-enter:

1. **"There is no reverse proxy in front of the API."** False — `frontend.conf` proxies
   `/api/`. The 413 this contract specifies was unreachable for every browser, while
   acceptance tests hitting `BACKEND_PORT` would have gone green on it.
2. **`Generation._is_blank_topic`** does not exist; it is the module-level `required_topic`.
   A grep for the cited symbol returns documentation only.
3. **"Normalized 1..60"** — a lower bound that nothing can violate and that contradicts
   blank-clears-with-200 two paragraphs above it.
4. **"`session.get` consults a request-scoped identity map, so `/me` adds no second
   SELECT."** False — the session is per *dependency*, so there are two of each.

Two of the four were load-bearing: they were the stated reason a guard was *not* specified.
