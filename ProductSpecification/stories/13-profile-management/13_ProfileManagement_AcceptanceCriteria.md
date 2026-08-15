# Profile management — Folded Hazard-Scan Guards

Every guard below came from the Phase-4 hazard scan (groups 1–8, 2026-08-13) and is written
so a downstream test can go red on it. Grouped by area, not by catalogue group — several are
one guard closing a seam two passes found from different sides. The scan record is in
`tests/00_Hazard_Scan_Record.md`.

## Persistence & the hand-enumerated write path

**One db test against real Postgres carries four hazards at once** (encoding, idempotency,
identity-map blindness, silent non-write). It must: write through
`SqlAlchemyAccountRepository.save()`, re-read in a **separate session** (`expire_on_commit=False`
plus `session.get`'s identity map means a same-session re-read passes on a row Postgres never
received), cover **both** the INSERT and UPDATE paths (`from_domain` already silently drops
`failed_attempt_count`), and use a **maximal-astral, NFD** fixture, not `"Иван"`.

- Rename a **verified** account with `failed_attempt_count > 0`; re-read the whole row and
  assert `is_verified` still true, `failed_attempt_count` unchanged, `email` and `created_at`
  byte-identical. Red on a rename that rewrites the aggregate.
- Capture emitted SQL (`before_cursor_execute`, idiom in `test_generation_storage_cas_shape.py`)
  and assert the rename is a single UPDATE setting only `name`. **An `asyncio.gather` of two
  PATCHes is not this guard** — that file's docstring records that the coroutines serialize and
  the test certifies the bug green.
- Save the same account twice (or PATCH twice with the same body): exactly one row for that id,
  final `name` correct, no `IntegrityError`/500 on the second.
- After clearing, a **fresh** session returns `name: null` — not the prior name, not the DTO
  echo. The clear direction is where a truthiness-guarded assignment answers 200 and changes
  nothing.
- With two named accounts, PATCH one and re-read the other: `name` and `email` unchanged.
- A newly registered account starts at `NULL`, never `""`.
- 60 × U+1F600 (60 code points / 120 UTF-16 units / 240 UTF-8 bytes) round-trips byte-exact
  through PATCH → row → GET. Red on a byte-bounded column, a UTF-16 `maxLength`, or truncation.
- NFD input is stored and returned canonically equivalent to, but not byte-equal to, the request.
- A wiring test asserts the rename usecase holds a real `SqlAlchemyUnitOfWork` on the
  repository's session (shape of `test_login_wiring.py`, which exists because a default
  `NullUnitOfWork` makes `commit()` a silent no-op with zero symptom), and `commit()` is called
  once on success and never on the 400 path.

## Request boundary

- One test per server-owned field on `PATCH /me` — `email`, `is_verified`, `created_at`,
  `password_hash`, `failed_attempt_count`, `id`/`account_id`/`owner_id` — sent alongside a valid
  `name`, asserting the **re-read row** is unchanged for it. The draft had an output allow-list
  and no input one; `save()`'s update branch persists whatever reaches the aggregate.
- Three presence tests on an account that already has a name: `{}` → unchanged; `{"name": null}`
  → cleared; `{"name": ""}` → cleared. With the obvious `name: str | None = None` model the first
  two are indistinguishable, so the model must carry presence for these to differ.
- A name of only zero-width/format characters (U+200B, U+FEFF, U+00A0) clears the name — it must
  never persist as a set-but-unrenderable value, which would defeat the NULL-keyed email fallback
  and render a blank identity with `aria-label` ending in «Меню профиля: ».
- **Added at `/api-spec`, because the three characters above are exactly the ones the borrowed
  predicate already caught** — a test over them proves nothing about the rule's edge:
  - A name of only U+3164 (Hangul filler, `Lo`) or U+2800 (Braille blank, `So`) clears too.
    Neither is whitespace nor `Cf`, both render as nothing, and under the first draft's rule
    both persisted as the blank identity the rule exists to forbid.
  - A name of a single NUL (U+0000) and a name containing a lone surrogate each answer
    **400 `INVALID_NAME`** —
    not 200, and above all not the **500** that reaching Postgres's `text` type produces.
    Same hole as known-debt #8 on the topic predicate, arriving here as a contract violation.
  - `{"name": 123}` (and `[]`, `{}`) answers 400 `INVALID_NAME` in the canonical envelope —
    never FastAPI's 422, whose body echoes the rejected input back.
- Exact boundaries: 60 accept / 61 refuse (normalized), 256 accept / 257 refuse (raw).
- An NFD fixture of 60 NFC characters written as base+combining pairs (120 raw code points, 60
  after NFC) is **accepted 200** — red if the bound is applied before normalization.
- The raw-cap and normalized-bound refusals carry **distinct `error_code`s**. `Email` raises the
  identical message at both stages, so no test there can prove the cheap gate ran at all.
- `<script>alert(1)</script>` and `" onmouseover="alert(1)` saved as names render literally in
  the header and on the profile screen — no element created, no handler bound — including the
  initials/`aria-label` attribute sink. The header is a global sink, so this is the widest stored-
  XSS surface in the app. No `dangerouslySetInnerHTML` on this value.
- A bidi-override character (U+202E) in a name does not reorder surrounding header text. Note
  this is **not** the escaping guard above and is not satisfied by escaping: it needs bidi
  isolation at the sink (`<bdi>` or `unicode-bidi: isolate`).
- An oversized body (e.g. 10 MB `name`) is refused at the boundary, not after full buffering —
  and the assertion is made **through the frontend origin** (`app_url`), not only through
  `BACKEND_PORT`. `infra/docker/nginx/frontend.conf` proxies `/api/` and carries no
  `client_max_body_size`, so its 1 MiB default currently answers first with an HTML error page:
  a backend-port-only test is green on a path no user takes. The nginx cap must be set above
  the app's, and CI must pin that (`frontend/scripts/check-nginx-503.mjs` already reads the file).
- Every failure family answers `{error_code, message}` exactly — no extra keys, no stack-trace
  markers, no SQL keywords, no paths. The over-length case must reach the domain path and **not**
  FastAPI's `RequestValidationError`, whose 422 body echoes the rejected input back.
- A structurally valid token whose account row is gone → the same 401 as a forged token.
- A token whose type claim is absent or is neither `access` nor `refresh` → 401.
- Both routes: three 401 causes (absent header, refresh-typed, `exp` one second past with the
  clock fixed) and the just-before-expiry case answering 200.

## Wire contract & time

- The `/me` response built from an account whose `created_at` carries a **non-UTC offset**
  serializes as a `Z`-suffixed UTC instant (`"2026-03-14T09:26:53Z"`), matching `ProjectItemDto._as_utc`.
  A **naive** `created_at` raises, naming the field — `astimezone(UTC)` does not raise on a naive
  datetime and is silently correct in a UTC container, silently shifted on a dev machine.
- On an account that never set a name, the 200 body has `name` **present and null** — strict
  equality on the parsed field, not "contains". The frontend fallback hangs on which of
  present-null vs key-omitted ships.
- Both routes answer `Cache-Control: no-store`.
- With a sentinel email and sentinel name seeded, drive 401, over-length 400, and a forced 500 on
  both routes with the log appender captured: the sentinels appear in neither response body nor
  log output.

## Migration

- Applied to a table holding pre-existing account rows, the pre-story paths (register, verify,
  login, resend) still succeed and no pre-existing row is altered — N-1 code against N schema,
  which is live rather than theoretical because instances roll one at a time.
- upgrade → downgrade → upgrade leaves pre-existing rows' `email`, `is_verified`, `created_at`,
  `failed_attempt_count` and the row count intact. The sibling migration
  `f7b8c9d0e1a2_accounts_failed_attempt_count.py` really does `op.drop_column` on downgrade, so
  a rollback destroys every name entered since deploy — accepted and stated, not discovered.

## Client identity snapshot

- Hold `GET /me` open, PATCH a new name, resolve the PATCH first, then release the stale GET:
  header and screen show the PATCHed name and still do after the late response lands.
- PATCH name A then name B, resolve B before A: the UI shows B and still shows B after A lands.
- Hold account A's `/me` open, sign out, sign in as B in the same tab, release A's response: the
  header shows B, and a `ProfileMenu` mounting after the switch reads B, never A's resolved value.
  This is a cross-account identity leak, strictly worse than a stale name.
- After a session change where `/me` answers 401 or times out, the header shows **no** identity —
  never the previously fetched one.
- **A failing `/me` never signs the user out** (added at `/api-spec`). A 5xx, a timeout, and a
  401 whose renewal then fails each leave the stored session intact — `clearSession()` is not
  reached. `performRenewal` ends the session on *any* renewal failure by design, and this story
  puts `/me` on every page at boot, so without this guard a blip during a rolling deploy signs
  out every open tab and takes typed-but-unsaved editor content with it.
- After `clearSession()` with no subsequent sign-in, no `sessionStorage`/`localStorage` key and no
  DOM node contains the sentinel email or name.
- After a 400, the shared snapshot is unchanged.
- Two mounted `ProfileMenu`s under one failed shared fetch land in the **same** state.

## Client behaviour & rate

- Two mounted headers on one page issue **exactly one** `GET /me`; navigating between two
  authenticated routes issues no second one. Every existing AC about rendered content passes at
  two requests, so only a request-count assertion catches the fan-out.
- The `/me` call carries a timeout, aborts on unmount, and retries are capped with backoff and
  jitter — a blip or a rolling deploy otherwise has every tab retrying in lockstep.
- Double-click Save and double-Enter each produce exactly one `PATCH`.
- Stubbed `/me` states each assert their defined header UI: in flight → placeholder; failed →
  degraded identity **distinct** from the placeholder; 200-with-missing-fields → no crash and no
  `undefined` fed to initials on every page in the app. «Выйти» present and functional in all.
- A 5xx and a 4xx are distinguishable in behaviour, not collapsed into "failing".
- The client length counter counts code points: 60 emoji reads 60/60, submit enabled, save 200;
  61 marks over-limit and the same request sent past the UI is refused 400. `.length` counts
  UTF-16 and would disagree with the server by 2× on any non-BMP name.
- `accountInitials` with a name whose first character is astral (`"𝒜лиса"`) or a base+combining
  pair yields one valid grapheme — no U+FFFD, no lone surrogate. `word[0]` is safe on ASCII-ish
  email local parts by accident and is not safe on a name.
- Typed-but-unsaved name: in-app navigation and refresh both guard or restore; a header `/me`
  answering 401 mid-edit does not silently drop the typed value.
- The registration date renders through the existing `formatCardDate` (unparseable → `—`,
  sentinel-year bounds, ru-RU genitive month) rather than a third hand-rolled formatter, with the
  test's `TZ` **pinned to a non-UTC zone** — a date test passing only under the CI ambient is
  drift, not coverage.

## Load

`GET /me` becomes the highest-rate endpoint in the product. A load scenario drives it at the
page-view rate implied by hundreds of concurrent users and asserts sustained rate without
connection-pool exhaustion, with checked-out connections returning to baseline.

**Sized against two connections per request, not one** (corrected at `/api-spec`).
`request_scoped` opens one session per **dependency**, and `create_account_existence` is
itself `@request_scoped`, so `get_current_owner_id`'s existence check and the profile read
run on separate sessions: two `SELECT … FROM accounts`, two simultaneous checkouts, two
`pool_pre_ping` round-trips, against SQLAlchemy's default 5 + 10 overflow per process. A
SQL-capture test (`before_cursor_execute`, as in `test_generation_storage_cas_shape.py`) pins
the per-request SELECT count so the load scenario's premise cannot drift silently. Whether to
collapse it to one connection is an ADR due before the backend scenarios.

This **revises**
the interview's Performance paragraph, which declined a load scenario on the grounds that the
story adds no queue, no external API and no table scan — true, and beside the point under a
Throughput profile whose binding constraint is request rate.
