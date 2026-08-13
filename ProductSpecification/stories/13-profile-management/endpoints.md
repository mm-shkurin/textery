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

**Blank reuses `Generation._is_blank_topic`'s definition** — whitespace *and* category
`Cf`. A name of U+200B or U+FEFF must clear rather than persist: a set-but-unrenderable
name defeats the NULL-keyed email fallback and truncates the avatar's `aria-label` to
«Меню профиля: », destroying the one job that row has.

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

**A missing account is 401, never 404.** No route on this story takes an account
identifier, so there is nothing to enumerate and no ownership check to get wrong; a
structurally valid token whose row is gone gets the same refusal as a forged one.

## Constants pinned here

| Constant | Value | Why |
|----------|-------|-----|
| Raw `name` cap | 256 code points | Cheap pre-normalization gate, per `Email`/`Password`. Generous on purpose: NFD is longer than NFC and must not be cut off before it is normalized. |
| Normalized `name` bound | 1..60 code points | Code points, like story 12's `q` and story 7's password length — never bytes, never UTF-16 units. |
| Request body cap | 2 MiB, app-wide | Fixed by the largest legitimate body in the product, not by this route: `documents_save` allows 200 000 code points, up to ~800 KB as UTF-8 before JSON escaping. See `api-specs/README.md`. |
| `Cache-Control` | `no-store`, both routes | The body carries the account's email. |
| Concurrency control | none (last-write-wins) | A display name; a lost update costs one retype. |

## Not decided here

The write path has no failure *screen*: all eight mockups cover reading plus one client-side
validation, so the 5xx and network-drop states of `PATCH` are contract-only. That gap is
already recorded as an ACTION on `13_ProfileManagement.md` § Screen States, due before
`/test-spec`; this file gives that state its API side (413/500 in the canonical envelope,
nothing persisted, the typed value still the client's to keep).
