# Story 12: Мои проекты — Backend Progress

Bootstrapped 2026-08-01 from `tests/01_API_Tests.md`, `tests/06_Integration_Tests.md`,
`tests/05_Security_Tests.md`, `tests/03_Load_Tests.md`, `tests/04_Infrastructure_Tests.md`
(spec phase complete — see `progress.md` for the Spec checklist and narrative). Owns:
Backend, Integration, Security, Load and Infrastructure Scenarios (acceptance steps stay
inline per scenario). Frontend scenarios live in `progress-frontend.md`.
`ProductSpecification/stories.md` is the cross-file rollup.

**Open contract questions raised by the pre-commit review passes on `084d39d4`** — each
must be settled in `endpoints.md` at the `design` step of the scenario that first hits it,
not silently resolved in code:

1. `GENERATION_STALE_AFTER_MINUTES` — required at boot, or defaulted to 10? API 1.10 and
   Infra 3.2 cannot both hold as written (first hit: Scenario 1.9).
2. Retry ceiling — per source row or per lineage? Per-row lets A→B→C bypass the money cap
   (first hit: Scenario 8.9).
3. The search query in the log — carried as a field (API 6.6) or redacted (Security 7.2)?
4. `POST /generations` with no `Idempotency-Key` — accepted with a NULL key, or 400? A
   400 breaks the deployed client and contradicts Infra 2.4 (first hit: Scenario 9.1).
5. Does a replayed retry key consume the source's retry budget? Unpinned (first hit: 8.3).
6. Is a completed search's slot released on the success path? 10.4's title claims every
   exit path; its body tests only the deadline (first hit: Scenario 10.3).
7. `status: running` (API 1.9) is not in the contract enum — `in_progress` is.
8. One 409 code for "not failed": `NOT_RETRYABLE` or `GENERATION_NOT_FAILED`.
The group-8 scan at 1.1's `design` step raised a #9 — that the retry endpoint has no slot
for an idempotency key — and it was **false**: `api-specs/generations_retry.yaml` declares
a required `Idempotency-Key` header keyed on `(owner_id, Idempotency-Key)`, with
`IDEMPOTENCY_KEY_REUSED` and a 200 replay. Struck rather than answered; a scan reading
only the design draft could not see the contract.

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1 The feed shows the caller's documents and nothing of anyone else's
- [x] red-acceptance
- [x] design (Option A — see `decisions/project-feed-read-model-decision.md`; hazard scan:
  groups 1–8, 8 GAPs folded into the design, 3 folded as Scenarios 11.1–11.3, 1 dismissed
  to Scenario 10.6, 2 withdrawn as duplicates of 8.3/8.5 and 7.2/7.4, group 8's UI
  sub-triggers dismissed as out of altitude)
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (Check 1 ports: `ProjectFeedRepository` has no implementation in
  any adapter module — the document is written through `DocumentStorage` (db) by the
  create-document usecase and must be read back through `ProjectFeedRepository.list_feed`
  (db), so the pair runs that write-port → read-port flow, not a same-port round-trip.
  `SearchSlots` → `[S]`: `ListProjects.execute` calls neither `acquire` nor `release` in
  1.1; the port is constructor-frozen for 10.1 and an implementation is owed there.
  Check 2 exceptions: `ValidationException(UNAUTHENTICATED)` is absent from
  `_ERROR_CODE_STATUS_MAP` in `error_handling/exception_handlers.py`, whose `.get(code, 400)`
  default answers 400 where `projects_list.yaml` declares 401 — rest pair.
  Check 3 response shape: `GET /api/v1/projects` is registered on no router and no
  `ProjectItem`/`ProjectListBody` DTO exists, while the acceptance test compares the whole
  parsed envelope (`items`, `page`, `limit`, `total`) — rest pair.)
- [x] red-adapter db
- [x] green-adapter db (documents arm only — the ADR's generations arm arrives with the
  scenario that first seeds a generation, so it cannot ship under zero test pressure)
- [x] red-adapter rest (UNAUTHENTICATED → 401)
- [x] green-adapter rest (UNAUTHENTICATED → 401) — the entry is dead on the planned
  wiring: `get_current_owner_id` returns a non-optional `UUID` or raises the already-mapped
  `UNAUTHORIZED`, so nothing can emit `UNAUTHENTICATED` through the route. Whether 1.1
  should have reused `UNAUTHORIZED` rather than minting a synonym is open and owed a
  contract answer.
- [x] red-adapter rest (GET /api/v1/projects envelope) — pins `items` and the row's `id`
  only, both as whole-dict equality. `page`, `limit`, `total` and every `ProjectItem` field
  beyond `id` stay unpinned because the domain has no source for them yet.
- [x] green-adapter rest (GET /api/v1/projects envelope) — route + `ProjectItemDto`/
  `ProjectPageDto` (only `items` and `id`; `page`/`limit`/`total` stay unemitted), plus the
  owed wiring test `backend/application/tests/test_project_feed_wiring.py`:
  `create_list_projects` (`@request_scoped`) builds a real `ListProjects` over
  `SqlAlchemyProjectFeedRepository`, `SystemClock` and a new `UnlimitedSearchSlots`, and
  `main.app` overrides `get_list_projects_usecase` with it. `UnlimitedSearchSlots` grants
  unconditionally — it exists only to satisfy the ADR's frozen constructor; the real
  DB-backed per-account slot is owed at 10.1, and it must be DB-backed because the backend
  runs multi-instance. Coverage 96% lines / 100% branches on the rest module; the only
  uncovered touched lines are that class's `acquire`/`release` (10.1's work) and the
  provider's `raise NotImplementedError` stub — deliberately left uncovered, as it is in
  `document_router`, `generation_router`, `health_router` and `security/current_owner`, and
  the wiring test already pins that the override making it unreachable is installed.
- [x] widening decision (2026-08-04) — the blockage recorded below is resolved in favour of
  **widening the domain**, not narrowing the acceptance assertion. `test_project_feed_acceptance.py`
  and `ProjectFeedStatements` were written at red-acceptance and passed `/test-review`; the
  whole-envelope equality is what makes "the feed shows the caller's documents" a real claim
  rather than an id-only check, so weakening it would retire the scenario's own strictness to
  make a step reachable. The per-field deferral notes in `ProjectItem`, `ProjectPage` and
  `ProjectItemDto` ("each arrives with the scenario that first asserts one") point here: 1.1's
  acceptance test IS the first assertion of every one of those fields. The widening follows the
  ADR's declared shape (`decisions/project-feed-read-model-decision.md`: `ProjectItem(kind, id,
  title, preview, document_type, status, retryable, created_at, updated_at)`,
  `ProjectPage(items, page, limit, total)`), and is scheduled as the red/green passes below —
  row shape first, then the envelope counters, each through usecase → db → rest.
  Deliberately NOT pulled in: `sort`/`q` on `ProjectPageRequest` (3.x), the grapheme-aware
  preview trim beyond an empty-content document (no test pressure in 1.1), the generations arm
  (1.2/1.3), and real LIMIT/OFFSET paging behaviour (2.1/2.2) — 1.1 only pins the
  unparameterised defaults `page=1`, `limit=20` and a `total` that is a true count, not
  `len(items)`.
- [x] red-usecase (the feed row carries the contract's full shape) — `ProjectItem` widens to
  `kind`, `title`, `preview`, `document_type`, `status`, `retryable`, `created_at`,
  `updated_at` alongside `id`; the usecase test pins that `ListProjects.execute` returns them
  through unchanged from the port. One assertion, `asdict(page.items[0]) == _EXPECTED_ROW`,
  so a dropped field, a substituted one and an invented tenth all fail. `retryable` is seeded
  `True` on a `document` row — a pair the db arm will never emit — so a usecase that hardcoded
  the contract's document default `False` instead of forwarding the port's value cannot pass.
  `ProjectKind`/`ProjectStatus` enums deliberately NOT introduced: nothing here constrains the
  value *set*; the fail-closed unknown-status rule is first asserted in the db arm (1.7).
- [~] green-usecase (the feed row carries the contract's full shape) — must also patch
  `ProjectFeedStatements._documents_of`, which builds `ProjectItem(id=uuid4())` and breaks the
  moment the constructor widens (tdd-rules setup-method carve-out).
  **Review-pass findings on `df9abbdc`, to settle at this step** (both passes returned
  CONCERNS; surfaced, not auto-fixed):
  1. *agent-review, high* — the assertion is arguably a tautology. The fake returns the seeded
     instances and `execute` is a bare `return await …list_feed(...)`, so
     `asdict(page.items[0]) == _EXPECTED_ROW` reduces to a frozen-dataclass round trip. The
     green will therefore modify **zero** usecase production files — only the domain VO — which
     is the `[S]` shape in `tdd-rules.md`. Decide at green: either mark this pair `[S]` and let
     `red-adapter db` carry the field pressure where the values are actually produced, or keep
     it as the domain-widening vehicle and say so explicitly.
  2. *agent-review, medium* — `ProjectItem`'s committed docstring says `kind` is deferred to
     scenario 1.8 and the other fields to "the scenario that first asserts one". The green makes
     that docstring false; correct it in the same commit.
  3. *premortem, credible* — the cheapest green gives the eight new fields **defaults**, so
     `ProjectItem(id=…)` stays legal and `project_feed_storage.list_feed` keeps emitting hollow
     rows with every test green. Guard named: a shape statement asserting the field names equal
     the nine contract names AND every `default`/`default_factory` is `MISSING`
     (`port_shape_statements.py` already has the reflection idiom).
  4. *premortem, credible* — `ProjectItemDto.from_domain` returns `cls(id=item.id)`; Pydantic
     does not object to source fields a DTO ignores, so it keeps compiling and keeps serializing
     `id` alone after the domain widens. The only test that would notice is 1.1's skipped
     acceptance test. Guard named: a spec-vs-DTO test comparing `ProjectItemDto.model_fields`
     against the `required` set of `#/components/schemas/ProjectItem` in `projects_list.yaml`.
     Belongs to the `red-adapter rest` pair below.
  5. *premortem, credible* — `reason="RED: …"` skips outlive their green commit in this repo,
     demonstrably: `test_login_lockout_acceptance.py` has carried one since 2026-07-22 and
     `test_auto_editor_transition_acceptance.py` since 2026-07-29. This is the only usecase-layer
     test asserting field pass-through, so a surviving skip loses the whole claim. Guard named: a
     meta-test over collected items failing on any `RED:` skip outside an allowlist. Out of
     scope for story 12 — belongs to a task.
- [ ] red-adapter db (every row field projected from the documents arm) — `title`, `preview`
  (empty content ⇒ `''`), `document_type`, `status`, the two timestamps read from
  `DocumentModel`; `kind` the literal `document`; `retryable` false for every document.
- [ ] green-adapter db (every row field projected from the documents arm)
- [ ] red-adapter rest (the envelope emits every `ProjectItem` field) — `ProjectItemDto` widens
  to the contract's nine fields, timestamps serialized as UTC ISO-8601 with an explicit offset
  (the acceptance DTO's `parse_feed_timestamp` rejects a naive string).
- [ ] green-adapter rest (the envelope emits every `ProjectItem` field)
- [ ] red-usecase (the envelope carries page, limit and total) — `ProjectPage` widens to
  `(items, page, limit, total)` and `ProjectPageRequest` grows the contract's unparameterised
  defaults `page=1`, `limit=20`; the usecase test pins that they reach the caller.
- [ ] green-usecase (the envelope carries page, limit and total)
- [ ] red-adapter db (total is a counted total, not `len(items)`) — the window count of the
  ADR, so a page holding one row of one still reports the true count and an owner with nothing
  reports zero.
- [ ] green-adapter db (total is a counted total, not `len(items)`)
- [ ] red-adapter rest (the envelope emits page, limit and total)
- [ ] green-adapter rest (the envelope emits page, limit and total)
- [ ] green-acceptance — was BLOCKED as the steps above originally stood: 1.1's acceptance test
  parses the whole envelope through `ProjectListBodyDto.from_json`, so it raised `KeyError` on
  `page`/`total`/`kind`/`title`/… which no layer emitted. The widening passes above are what
  unblock it; this step stays a remove-marker-only run.

### Scenario 1.2 A generation that became a document appears once, as the document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3 A completed generation with no document is surfaced
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4 A failed generation is surfaced and marked retryable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5 A generation stuck past the stale threshold is marked recovering and not retryable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6 Every generation status has a defined feed outcome
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.7 An unrecognized generation status fails closed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.8 A document and a generation sharing an id are two distinct items
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.9 The recovering label flips exactly at the stale threshold, in its declared unit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.10 A missing or unparsable stale threshold fails closed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.11 A feed of known statuses emits no unknown-status signal
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 Paging a static feed returns every row exactly once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2 The reported total counts the deduplicated feed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3 An empty feed reports a total of zero
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4 A page past the end is empty, not an error
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.5 The page and its total come from one consistent read
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.6 A just-created project is visible to the very next request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.7 One page costs a fixed number of storage queries whatever the feed's size
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1 Each sort order returns the feed in that order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2 Rows sharing a sort key keep a stable order across repeated reads
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3 Untitled projects sort last by title
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4 Title ordering does not depend on the database's ambient locale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5 Generations are ordered alongside documents, not after them
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.6 An unrecognized sort order is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.7 A sort whose key ties across a page boundary returns each row exactly once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1 Search matches title, generation topic and document content
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2 Search is case-insensitive and normalization-stable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3 Search matches wildcard characters literally
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4 A whitespace-only query behaves as no search
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5 Search combines with sorting and paging
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.6 Search never crosses account boundaries
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.7 Case-folding does not depend on the session's locale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1 A page or limit outside its range is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2 A non-integer page or limit is refused, not truncated
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3 A search query over the length bound is refused, measured in code points
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4 A page or limit beyond the integer type is refused, not overflowed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5 Omitted, empty and repeated parameters have pinned outcomes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1 The list never returns full document content
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2 Preview truncation does not split a character
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.3 Stored markup is neutralized in every echoed field
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.4 Timestamps are returned as UTC instants
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.5 Multibyte text survives storage and listing unchanged
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.6 Attacker-controlled values cannot forge a log record
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1 Retrying a non-existent or foreign generation is refused indistinguishably
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.2 Retrying a generation that is not failed is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.3 A missing or oversized idempotency key is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.4 Retrying a generation in an unrecognized status is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1 A retry creates a new generation from the source's stored parameters
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.2 The failed source stays in the feed beside the new generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.3 A duplicate retry produces one generation (inbound)
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.4 A retry whose response was lost creates no second generation (outbound)
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.5 Concurrent retries across instances produce one generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.6 One account's key never matches another account's record
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.7 A fresh key after a terminal outcome starts a new generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.8 The same key against a different source is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.9 Retries of one source are capped
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.10 Idempotency keys are compared exactly
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.11 The retry at the ceiling is accepted and only the next is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.12 Concurrent retries at the ceiling cannot exceed it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.13 A retry's generation starts in the initial status, not the source's
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.14 A retry that fails on its last write leaves no orphan
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.1 A replayed create key returns the existing generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.2 Pre-existing generations without a key are unaffected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.3 The create endpoint ignores server-owned fields and does not rebind on replay
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.4 The deprecated list endpoints keep their behaviour
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.1 A query that exceeds the deadline fails generically
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.2 The deadline does not leak onto the shared connection
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.3 A second concurrent search for one account is shed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.4 A shed slot is released on every exit path
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.5 An abandoned slot is reclaimed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.6 The feed is not stored by shared caches
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.7 A request whose authorization cannot be resolved is denied
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.8 The search slot is held for its whole lifetime and no longer
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.9 Two searches claiming the slot at once yield exactly one holder
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.10 Repeated failures return every acquired resource to baseline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.11 A shed request tells the caller when to retry
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.12 A caller that gives up leaves no scan running
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.13 The correlation id in the response is the one in the log
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10.14 Each degraded path emits a distinguishable signal
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Discovered by the hazard scan at Scenario 1.1's `design` step (2026-08-02)

Three fired triggers whose forced guard no existing scenario carries. Folded here as named
scenarios rather than dismissed; the guards the *design* absorbed are recorded in
`decisions/project-feed-read-model-decision.md` instead. Group in brackets. (5.5 pins
omitted/empty/repeated for `sort` and `q` only, which is why 11.2 is not a duplicate of it.)

### Scenario 11.1 A document written before generation_id existed shows its work once [group 4]
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 11.2 A feed requested with no limit is capped at the server default [group 6]
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 11.3 A row inserted between two page requests is neither skipped nor served twice [groups 3, 6]
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

Group 8's other two fired triggers were folded and then withdrawn: "two retries before the
first responds" is 8.3 + 8.5, and "retry re-checked on the server" is 7.2 + 7.4. Both
already carry their guard.

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1 An accepted retry enqueues exactly one job for the new generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2 A replayed retry key enqueues no second job
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3 A retry whose enqueue fails leaves no generation the worker will never pick up
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4 A retry that stored its generation but lost the response is not enqueued twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5 The enqueued job carries the source's stored parameters, not client input
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6 A retry whose commit fails leaves no job behind
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.7 An enqueue that times out resolves to a defined outcome
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.8 A generation whose enqueue was lost is still picked up
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 The sweep does not requeue a generation the user has already retried
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2 A row the sweep is currently requeueing cannot be retried by the user
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3 A retry and a sweep requeue racing on one source produce one running generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4 A generation whose document was written but never marked terminal is not run again
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.5 One row failing mid-sweep neither rolls back nor blocks the rest
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.6 Two sweep activations do disjoint work
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.7 An always-failing generation stops being requeued and does not stall the queue
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1 A retried generation that completes replaces its card with a document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2 A retried generation that fails again is retryable once more within the cap
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3 A worker outcome written while the caller is paging does not corrupt the page
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4 A job delivered twice for one generation produces one document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1 No parameter combination reveals another account's rows
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2 The reported total counts only the caller's rows
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3 An owner supplied by the client is ignored
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 Search input reaching the query cannot alter it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2 A sort value cannot reach the query as a column name
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1 Markup stored in any echoed field is neutralized
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1 Retrying another account's generation is refused indistinguishably
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2 An idempotency key cannot reach another account's record
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1 The retry cannot set server-owned fields
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1 One source generation cannot be retried without bound
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2 Search cannot be used to occupy the database
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1 Failures expose nothing internal
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.2 Credentials, keys and user text never reach the log
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.3 An unmapped failure returns the sanctioned envelope
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1 A client-supplied preview is ignored
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1 The projects feed sustains its request rate under concurrent users
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 Concurrent searches do not degrade the unsearched feed's rate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2 Excess concurrent searches are shed rather than queued
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1 The feed fails cleanly when the database is unavailable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2 The feed recovers once the database returns
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 The migration completes on a table that already has generations
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2 The new constraint holds for new rows without rejecting old ones
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3 The migration does not block the running sweep
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4 The previous code version keeps writing against the migrated schema
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1 A required constant that is unset or unparsable stops startup
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2 A documented default is in effect and observable when its variable is unset
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1 Reclaiming an expired search slot leaves live slots intact
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

