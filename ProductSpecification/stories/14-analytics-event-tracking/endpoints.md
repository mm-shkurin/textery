# Analytics Event Tracking — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/analytics/events | Record one browser-origin event (`SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED`). The product's only tokenless write. |
| POST | /api/v1/auth/register | **Extended, not modified.** Body gains the five optional `utm_*`; `Accept-Language` becomes the source of the stored device language. **No response changes**: same status codes, same `error_code` set, same bodies. |
| GET | /api/v1/auth/oauth/{provider}/start | **Extended, not modified.** Gains the five `utm_*` as optional query parameters. **No response changes**: still `302 / 404 / 500`, and in particular still no `400`. |

Contracts: `api-specs/analytics_events_create.yaml`, `api-specs/auth_register.yaml`,
`api-specs/oauth_start.yaml`.

> **The two extended routes are additive only.** Every request that these two endpoints accept
> today is accepted after Story 14, with the same status code and the same body; every request
> they refuse today is refused the same way, with the same `error_code`. The `utm_*` are
> analytics metadata riding along — they can be stored or not stored, and nothing else about
> the call changes. This is the Governing Decision in `14_AnalyticsEventTracking.md`, agreed
> with the developer on 2026-08-19; it supersedes the earlier draft of this file, which had
> over-bound attribution returning `400` from `/auth/register`.

**One new endpoint, not a resource.** No `GET /analytics/events`, no aggregate, no export —
reading is Story 15 and building a read surface here would hand it a contract it has not
designed yet. Five of the eight live events (`REGISTRATION_COMPLETED`, `LOGIN_SUCCESS`,
`GENERATION_STARTED`, `GENERATION_COMPLETED`, `DOCUMENT_SAVED`) have **no HTTP surface at
all**: they are emitted in-process by the usecase that performed the transition, which is
also what makes them unforgeable.

## Decisions this step had to make

### The accepted set is three names, not twelve

The catalogue declares twelve and the column's CHECK constraint lists all twelve, so
Stories 8/9 can start emitting the subscription names without a migration. The **route**
accepts only the three a browser legitimately produces. Anything else — the nine
server-only and subscription names included — is `400 UNKNOWN_EVENT_NAME`.

Written as "accepted by the contract, no client is allowed to send them", the rule had no
enforcement: on a tokenless endpoint that means anyone with `curl` can write
`SUBSCRIPTION_ACTIVATED` rows into the table Story 15 computes revenue from. Narrowing the
enforced set also removes forged `GENERATION_COMPLETED` and `LOGIN_SUCCESS` in the same
move, at no cost to any real client.

### 204, not 202

202 says "accepted, will be processed" — which would make the read-after-write guard
unassertable and hand Story 15 an unstated staleness window. The row is committed before
the response returns and is readable on another connection by then. Nothing to return, so
204 rather than 201 with an empty body.

### `occurrence_key` is a client-minted UUID, and a repeat is a 204

React StrictMode double-invokes effects and the second request is genuinely sent —
`useGeneratedDocumentInit.ts` records exactly this ("suppresses the second run's setState
but NOT its request"). A client cannot unsend it, so the collapse is server-side. A UUID
rather than a free string sidesteps a length bound and a normalization question entirely.

Deliberately not `Idempotency-Key` in a header, though `POST /documents` uses that shape:
this key identifies *the occurrence being reported*, not *the HTTP attempt*, and a client
retry of the same occurrence and a StrictMode double-fire must collapse identically.

### Every bound is a number, with its unit

The scan found the repo already measures size two ways — bytes at the transport boundary,
code points in the domain — so an unnamed bound is an ambiguous one.

| Thing | Bound | Unit | Over the bound |
|---|---|---|---|
| `payload`, serialized | 4096 | bytes | `400 INVALID_PAYLOAD` |
| `payload` nesting depth | 8 | levels | `400 INVALID_PAYLOAD` |
| `payload` keys, total | 64 | keys | `400 INVALID_PAYLOAD` |
| Request body (this route) | 16384 | bytes, on bytes actually read | `413 REQUEST_BODY_TOO_LARGE` |
| Each `utm_*` | 200 | code points, after NFC | **the attribution set is dropped; the call answers unchanged** |
| Rate limit (this route) | 120 per 60 s | requests per bucket | `429 RATE_LIMITED` |

The last column is where this contract stopped being uniform, deliberately. The first four
bounds guard the **new** endpoint, where a refusal costs a lost analytics row. The `utm_*`
bound sits on **two existing auth routes**, where a refusal costs a user their registration —
so there the bound decides what gets *stored*, never what gets *answered*.

Depth and key count are separate from the byte cap on purpose: 4 KiB of `[[[[…]]]]` is
under the size limit and still meets Python's decoder as a `RecursionError`, i.e. a 500 on
a request that passed validation.

### Attribution is fail-open on both auth routes (`A1 + B2`)

Decided with the developer on 2026-08-19, and the reason this file was revised. The draft had
an over-bound `utm_campaign` answering `400` from `POST /auth/register`. That is a new way for
registration to fail, invented by an analytics attribute, on the most sensitive route in the
product — and it is exactly what the story's own criterion "a failure anywhere in the analytics
path never changes the outcome of registration" forbids. A visitor who clicks a marketing link
with a malformed parameter must not be told they cannot create an account.

The rule, on `POST /auth/register` and `GET /auth/oauth/{provider}/start` alike:

| Input | Stored | Answered |
|---|---|---|
| Five usable values | all five | unchanged |
| Some absent or empty | those NULL, the rest kept | unchanged |
| Any member over the bound | **nothing — all five NULL** | unchanged |
| Any member undecodable (cp1251 link) or holding text the store cannot take (NUL, lone surrogate) | **nothing — all five NULL** | unchanged |
| No `utm_*` at all | all five NULL | unchanged |

"Unchanged" is literal: the same status code, the same body, the same `error_code` set, the
same redirect. There is no new `error_code` anywhere in this story outside
`POST /api/v1/analytics/events`.

**Why the whole set and not the bad member (`B2`).** Dropping one member would write
attribution sets into the database that no marketing link ever produced — `utm_source` present,
`utm_campaign` silently missing — and Story 15 cannot tell that apart from a link that genuinely
had no campaign. Discarding the set keeps every stored attribution a faithful copy of one real
link. The cost is that one malformed parameter loses four good ones; that cost is paid in a
marketing report, not by a user.

**A discard is not silent to us, only to the user.** One structured log record names which
field failed the bound and why, carrying no value — the same treatment a swallowed emission
failure gets. Without it, an escaping bug in a campaign builder would zero out attribution for
a whole channel with nothing to see.

### OAuth sign-up gets attribution too — via `/start`, not the body

**The most consequential call in this step, and the one to veto if it is wrong.** The
account is created inside `/callback`, two redirects away from anything the client can put
in a body, so the obvious placement does not exist. Without carrying UTM through, every
account created via Yandex ID registers with NULL attribution — a working sign-up channel
absent from CAC-by-UTM, which is the metric the requirement exists to serve.

So `/start` accepts the five parameters and the backend parks them on the `oauth_states`
row it already writes, reading them back when the callback creates the account. They are
never forwarded to the provider.

`/start` is a redirect route: it answers `302 / 404 / 500` today and has no `400` at all. It
does not get one here. A parameter that cannot be stored is dropped by the rule above and the
visitor is redirected to the provider exactly as they would have been — a broken marketing link
must never end at a broken sign-in. This also means Story 16's contract keeps its existing
response set untouched.

The technical context needs no such trick: `/callback` is itself a browser request, so IP,
User-Agent and `Accept-Language` are present there exactly as they are at `/register`.

The alternative — accept that OAuth accounts have no attribution — was rejected because it
silently biases every campaign report toward the email channel, and nothing in the data
would reveal it.

### `visitor_id` is stated untrusted in the contract itself

Not a code comment: the schema description says the server never infers `user_id` from it
and that no security, billing or entitlement decision may key on it. Story 15 reads this
contract and would otherwise be entitled to treat a join key as an identity.

### Residual this contract does not own

A body that is not valid JSON at all (`{`, empty, `text/plain`) still answers FastAPI's 422
in its own `{"detail": …}` shape rather than the canonical envelope. That mismatch predates
this story and is wider than it — `documents_save.yaml` documents a canonical-shape 422
FastAPI does not actually produce, and story 13 named the same residual. Closing it means an
app-wide `RequestValidationError` handler that changes the error contract of all 26 existing
endpoints. Not this story.

Consequence to respect while implementing: the request DTO must type `event_name`,
`visitor_id` and `occurrence_key` permissively enough that a bad value reaches the domain and
returns the canonical 400 — a strict Pydantic annotation would hand back a 422 that **echoes
the rejected input**, on an anonymous endpoint whose errors reach anyone.

**ACTION (`/test-spec`):** assert the canonical envelope for a non-string `event_name`, a
non-UUID `visitor_id` and an over-cap `payload`; pin malformed JSON as the one shape this
contract does not own.

## The five decisions the test spec was blocked on

`tests/00_Hazard_Scan_Record.md` listed five scenarios whose expected value was "whatever the
contract says", with no contract saying it. All five are answered here — four by the product
owner on 2026-08-17, the fifth by the developer decision of 2026-08-19. None of them changes
any existing endpoint.

### 1. `payload` absent, explicitly null, or `{}` — one stored representation: `{}`

The column is `NOT NULL` with default `{}`, and all three inputs store `{}`. A nullable JSON
column gives Story 15 two spellings of "no context" to handle at every read, forever, for no
gain. Answered `204` in all three cases. *(`extended/01` §1.1)*

### 2. One occurrence key reused under a **different** event name — `409`, nothing stored

Same `visitor_id` + same `occurrence_key` + same `event_name` → idempotent `204`, no second
row (that is the StrictMode collapse the key exists for). Same key with a *different*
`event_name` is not a replay of anything; it is a client bug or a probe, and collapsing it
would silently discard a real event while answering success. `409 OCCURRENCE_KEY_CONFLICT`,
nothing stored, the first row untouched. The key is unique **per visitor**, so two different
visitors sharing a key are two events and neither can probe the other's existence.
*(`extended/01` §3.1, and consistent with `extended/01` §3.2 / `extended/05` §2.2)*

### 3. A campaign parameter that decodes to replacement characters — not stored

The FOA rule above: the set is discarded, the registration or sign-in completes unchanged, and
a later visit carrying a readable link can still become the first touch. Mojibake is never
frozen as an account's permanent attribution. *(`extended/02` §2.1)*

### 4. Over-bound campaign parameters on the handshake — dropped, handshake proceeds

The FOA rule above. The scenario's two halves — "apply the contract's outcome" and "the visitor
is never left on a broken sign-in" — stop conflicting once the outcome is *drop*.
*(`extended/02` §2.2, `extended/06` §2.4)*

### 5. A generation with no recorded visitor — `analytics_events.visitor_id` is nullable

Every generation in flight when the migration lands, and every one created by an N-1 replica
during the rolling window, has no `visitor_id` on its row. The three options were a sentinel
visitor, an omitted event, or a nullable column.

- A sentinel invents a visitor who does not exist and pollutes every unique-visitor count with
  one enormous fake browser.
- Omitting the event loses a `GENERATION_COMPLETED` for a generation that really completed,
  and loses it silently.
- Nullable costs Story 15 one `WHERE visitor_id IS NOT NULL` in visitor-scoped queries.

Nullable. The browser route still requires `visitor_id` and still answers `400
INVALID_VISITOR_ID` without one — that is the new endpoint, where a rejection costs an
analytics row and nothing else. Story 15 is told in writing that a NULL visitor is a
server-emitted event from the migration window, and excludes those rows from visitor funnels.
*(`04_Infrastructure_Tests.md` §1.4a)*
