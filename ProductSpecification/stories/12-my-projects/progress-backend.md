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
- [x] green-usecase (the feed row carries the contract's full shape) — must also patch
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
  **Decision on finding 1 (2026-08-04): keep the pair, do NOT mark it `[S]`.** The green's
  production change lands in `domain` (`ProjectItem` widens to the ADR's nine fields), not in
  `usecase` — so "zero usecase production files" is true of the layer, not of the work. Marking
  it `[S]` would defer the VO widening to `green-adapter db`, which leaves this unit's `RED:`
  skip alive across work units — exactly finding 5. Keeping the pair kills the skip in the unit
  that opened it. The green owes, in the same commit: no defaults on any new field (finding 3's
  named shape guard), the corrected `ProjectItem` docstring (finding 2), and the fixed
  `ProjectItem(id=…)` call sites in `project_feed_statements._documents_of` and
  `project_feed_storage.list_feed` — the latter getting only what its committed tests demand,
  since the real projection is `red/green-adapter db`'s job.
  5. *premortem, credible* — `reason="RED: …"` skips outlive their green commit in this repo,
     demonstrably: `test_login_lockout_acceptance.py` has carried one since 2026-07-22 and
     `test_auto_editor_transition_acceptance.py` since 2026-07-29. This is the only usecase-layer
     test asserting field pass-through, so a surviving skip loses the whole claim. Guard named: a
     meta-test over collected items failing on any `RED:` skip outside an allowlist. Out of
     scope for story 12 — belongs to a task.
  **How the green settled each finding (2026-08-05):** (1) pair kept, per the decision above —
  the production change is `ProjectItem` widening to the ADR's nine fields in `domain`, and the
  `RED:` skip died in the same unit that opened it. (2) `ProjectItem`'s docstring rewritten: it
  now says all nine fields live here from 1.1 onward and none carries a default, replacing the
  per-field deferral text that the widening made false. (3) shape guard shipped —
  `usecase/tests/project/test_project_item_shape.py` + `statements/project_item_shape_statements.py`
  reflect over `dataclasses.fields(ProjectItem)`, pinning the nine names in declaration order and
  asserting every `default`/`default_factory` is `MISSING`, so no future default can restore the
  hollow-row hole. (4) NOT done here — the `ProjectItemDto`-vs-`projects_list.yaml` spec test is
  the `red-adapter rest` pair's, as recorded; `ProjectItemDto` still emits `id` alone and its
  docstring now says why (nothing asserts the other eight on the wire, and the storage adapter
  holds placeholders, not a projection). Call sites widened rather than defaulted:
  `project_feed_statements._a_document_owned_by_nobody_in_particular`, the rest router test's
  `feed_row` fixture, and `project_feed_storage.unprojected_row` — the last a named, exported
  factory whose docstring declares the eight fields it does not project yet, replaced wholesale by
  the `red/green-adapter db` pair below. Also fixed in passing: `db/tests/conftest.py`'s
  `project_feed_statements` fixture imported `statements.project_feed_statements`, a name that
  collides with the usecase tests' identically-named module under the same top-level `statements`
  package — a whole-suite run handed the db fixture the usecase Statements. Now imports
  `statements.project_feed_storage_statements.ProjectFeedStorageStatements` (class renamed to
  match its file). Tests: 653 passed, 62 skipped (whole backend). Coverage: touched production
  files at 100% line and branch (`project_item.py`, `project_response_dto.py`);
  `project_feed_storage.py` unmeasurable without a local Postgres (session-level skip), no gap
  opened by this green.
- [x] red-adapter db (every row field projected from the documents arm) — `title`, `preview`
  (empty content ⇒ `''`), `document_type`, `status`, the two timestamps read from
  `DocumentModel`; `kind` the literal `document`; `retryable` false for every document.
  **Review-pass findings on `0a4f6420`, to settle at this step** (both passes returned
  CONCERNS; surfaced, not auto-fixed):
  1. *both passes, high — verified against the yaml* — "the contract's **nine** required
     fields" is false. `api-specs/projects_list.yaml` `#/components/schemas/ProjectItem`
     declares `required: [kind, id, document_type, status, retryable, created_at, updated_at,
     preview]` — **eight** names — and `title: {type: string, nullable: true}` with "Null/blank
     sorts last under title_asc". The green typed `title: str` and the shape guard pins it
     required, so the domain now forbids a state the contract permits and Scenario 3.3
     ("Untitled projects sort last by title") depends on. This step must decide `title:
     str | None` and seed a NULL-titled document, rather than coercing NULL to `''` — which
     would destroy the null/blank distinction 3.3 asks about. Named guard: a shape assertion
     tying each field's annotation to the schema's `required`/`nullable`, read from the yaml
     rather than hand-copied into `EXPECTED_FIELD_NAMES` (the drift guard is what drifted).
  2. *both passes, high* — `project_feed_storage_statements.assert_feed_is_owner_scoped` now
     builds its expectation from `unprojected_row`, imported from the module under test, so
     both sides of the equality are one code path and the assertion has collapsed to
     `document.id == row_id`. Change `_UNPROJECTED_TIME` to 2099 and it stays green. This step
     replaces that expectation with a row built in the test tree from the seeded `Document`.
  3. *both passes, credible* — `unprojected_row` emits `kind=""` and `status=""`, values
     neither contract enum admits (`status` has an explicit fail-closed-to-`unknown` rule that
     a blank violates). Harmless only while `ProjectItemDto` serializes `id` alone — one line
     from the wire, and the db suite is session-skipped without a local Postgres so CI never
     executes the path. The projection this step lands removes the factory; if any placeholder
     survives it, it must be one that fails loudly.
  4. *premortem, credible* — the shape guard reflects over field *names* and defaults only,
     never `field.type`. A naive `datetime` from a `TIMESTAMP WITHOUT TIME ZONE` column keeps
     both shape tests green and breaks the contract's "UTC ISO-8601 with explicit offset".
     Named guard: assert `tzinfo is not None` on the timestamps of a row leaving the port —
     this step's arm, since it is the first to read them from `DocumentModel`.
  5. *premortem, remote; refactor-agent, adjacent* — the `statements` package collision is
     fixed by instance (rename), not by class: `db/tests/statements/` and
     `usecase/tests/statements/` are still one importable top-level package. Guard would be a
     meta-test on duplicate importable names, or `--import-mode=importlib`. Out of scope for
     story 12 — belongs to a task, alongside finding 5 of the previous unit (`RED:` skips
     outliving their green). Also out of scope and worth a decision: `backend-ci.yml` runs
     neither ruff nor mypy, and mypy reports 6 pre-existing errors — the `**_EXPECTED_ROW`
     unpack in `project_feed_row_statements.py:63` became untypeable with this widening.
  **How the red settled them (2026-08-05):** (1) the seeded document has a NULL title —
  `Document.create` never sets one — and the expectation pins `title=None`, not `''`; the green
  owes `ProjectItem.title: str | None`, since the frozen dataclass enforces nothing at runtime
  and the annotation is a lie until then. (2) `assert_feed_holds_only` no longer imports
  `unprojected_row`; it asserts the tuple of row **ids**, which is the owner-predicate claim and
  survives the green unchanged, while the nine-field expectation lives in a new
  `assert_row_is_projected_from` built in the test tree. `unprojected_row` now has zero importers
  outside its own module — **the green must delete it**. (3) the expectation pins
  `kind="document"` and `status="draft"`, so the `''` placeholders cannot survive. (4) both
  timestamps are pinned to fixed seeded literals 37 minutes apart, with `utcoffset() ==
  timedelta(0)` — not `tzinfo is not None`, which would wave through a `+05:00` row naming the
  same instant at a different wall clock, and not `updated_at` read off the entity, which
  `Document.create` sets equal to `created_at` so a projection emitting one column twice would
  have passed.
  **Environment note (2026-08-05):** the db adapter suite was session-skipped on this machine
  for want of a Postgres, so every earlier unit's "62 skipped" hid 60 unrun db tests. Docker
  Desktop was started and `infra/docker-compose.yml`'s `postgres` service brought up; the suite
  now genuinely executes. Whole-backend counts change accordingly: **713 passed, 4 skipped**
  (the 2 remaining skips beyond this step's RED pair are pre-existing). Any future run reporting
  ~653/62 is a run with no database, not a green suite.
- [x] red-adapter db (amendment — `title` and `preview` carry a real document's values)
  **Why this step exists.** Both review passes on `f1d8ee78` returned CONCERNS on the same
  point, and it is correct: the red pins `title=None` and `preview=""`, but the only seeded
  document comes from `Document.create`, which hardcodes `title=None` and `content=""`, and
  the production placeholder is `_UNPROJECTED_TEXT = ""`. Expectation equals placeholder, so a
  green that never selects `documents.title`/`documents.content` at all — emitting both as
  literals — passes. The commit applied the right standard to `document_type`/`status` and did
  not apply it to the two fields where the mirror is a constant rather than an echo. `preview`
  is the worse half: the contract makes it *derived* (required, non-nullable, bounded at 200
  code points, HTML stripped), and after `f1d8ee78` none of that derivation is under any test
  pressure. The green cannot repair this — a green may not change tests — so the amendment runs
  first. Seed a second document carrying a non-NULL title and non-empty content, and pin
  `row.title` and `row.preview` against those seeded values. 1.1 owes only the reading of the
  columns; the grapheme-aware 200-code-point trim stays 6.2's and the markup strip stays 6.3's.
  Also fold in while here:
  - *agent-review, medium* — the whole-page equality went out with the collapsed expectation.
    `assert_feed_holds_only` now asserts a tuple of ids and `assert_row_is_projected_from`
    compares `page.items`, so no db test compares a whole `ProjectPage` any more. The collapse
    being repaired was the `unprojected_row` import; `page == ProjectPage(items=(expected,))`
    would have fixed that while keeping the page-level guard the deleted comment existed to
    provide ("an assertion that reaches past the page into one field would keep passing while
    `page`/`limit`/`total` arrive unchecked").
  - *agent-review, low* — `SEEDED_STATUS` is not seeded and cannot be: `Document.create`
    refuses a status parameter by design and hardcodes `DRAFT_STATUS`. The hand-written
    `"draft"` is still not a mirror, so the assertion holds, but the name and the commit
    message both claim a seeding that does not happen — and a reader who later "fixes the
    duplication" by importing `DRAFT_STATUS` recreates exactly the mirror the comment warns
    against. Rename, or say so at the constant.
  **Checked and dismissed:** premortem's CREDIBLE 2 (the identity map masks the read, because
  `expire_on_commit=False` leaves the seeded `DocumentModel` resident, so an ORM entity select
  would re-assert the values Python wrote). The guard it asks for is already there —
  `ProjectFeedStorageStatements.list_feed` calls `self._session.expire_all()` before reading,
  with a comment giving that exact reason. The concern is real in kind and already answered.
  **Carried, not actionable now:** `status` is pinned only against `"draft"` because
  `ALLOWED_STATUSES = ("draft",)` and `ck_documents_status` rejects anything else, so a green
  hardcoding it cannot be caught until a second document status exists — the contract already
  lists `ready`. Belongs to whichever scenario introduces one, together with the ADR's
  fail-closed-to-`unknown` rule for the document arm.
  **How the amendment settled it (2026-08-05):** the second document is seeded through
  `Document.create_from_generation` — the only factory that accepts `content` and `title`,
  since `create`'s missing `content` parameter is the manual path's mass-assignment guard —
  and under an account of its own, so each test still reads a one-row page (1.1 owns neither
  ordering nor paging, and a two-row page would force an assertion on a sequence no scenario
  has specified). Row expectations moved to a new
  `db/tests/statements/project_feed_row_expectations.py`, mixed into the Statements class:
  a 200-line split, not a seam. Both row assertions compare the **whole page**
  (`page == ProjectPage(items=(...,))`), restoring the page-level guard the collapsed
  expectation had dropped. `SEEDED_STATUS` became
  `EXPECTED_STATUS_OF_ANY_SEEDED_DOCUMENT`, carrying at the constant the reason importing
  `DRAFT_STATUS` to "remove the duplication" would recreate the mirror. RED confirmed against
  a live Postgres: all three methods failed on the first run, the titled row coming back
  `title=''`, `preview=''` for a document seeded `title='Весна в городе'`,
  `content='Короткий текст.'` — the placeholder-equals-expectation hole, observed rather than
  argued. Timestamps failed on the *instants* (1970 vs the seeded 2026-03-01T09:15Z and
  +37min), not the offset: the placeholder is already tz-aware UTC, so that half of the guard
  correctly stayed silent.
  **`/test-review` (2026-08-05):** one fix applied — `SEEDED_UPDATED_AT` was
  `SEEDED_CREATED_AT + timedelta(minutes=37)`, a calculation in an expected value; it is now
  the literal `datetime(2026, 3, 1, 9, 52, 0, tzinfo=UTC)`. Dismissed: `retryable=False` is
  strict but unfalsifiable at 1.1 (no column to read; deferred to 1.2/1.3, recorded at the
  constant); `assert_feed_holds_only`'s id-only comparison is the owner-predicate claim, and
  tightening it would rebuild the removed mirror; the injected storage adapters *are* this
  layer's subject.
  **Open, for the green:** `ProjectItem.title` is annotated `str` while the contract declares
  it nullable and the expectation pins `None` — a frozen dataclass enforces nothing at
  runtime, so the annotation is a lie until the green widens it to `str | None`. Coercing NULL
  to `''` instead would destroy the null/blank distinction 3.3 depends on. The green must also
  delete `unprojected_row`, which now has zero importers outside its own module.
  **Out of scope, follow-up:** `assert_feed_refuses_an_unresolved_owner` combines action and
  assertion; splitting it edits `test_project_feed_storage.py`, untouched by this amendment.
- [x] green-adapter db (every row field projected from the documents arm) — `list_feed` selects
  `id, title, content, document_type, status, created_at, updated_at` from `documents` and maps
  each `Row` through a module-private `_row_of`; `unprojected_row`, `_UNPROJECTED_TEXT` and
  `_UNPROJECTED_TIME` are gone. A **column** select, not an ORM-entity select: `Row` tuples
  cannot be answered from the identity map at all, a stronger guarantee than the
  `expire_all()` the Statements already does, and it keeps the statement shaped for the ADR's
  eventual `UNION ALL`. `ProjectItem.title` widened `str` → `str | None` with the
  no-coercion warning on the field — NULL must not become `''` or 3.3 loses the null/blank
  distinction. Only two fields stay literals, each behind a named constant carrying its
  reason: `_DOCUMENT_KIND` (the UNION-ALL arm discriminator, no column exists) and
  `_DOCUMENTS_ARE_NEVER_RETRYABLE` (a generations-arm field, 1.2/1.3). `status` is read from
  the column rather than emitted as `"draft"` — the ADR's fail-closed-to-`unknown` rule stays
  unbuilt, still CARRIED and still untestable while `ck_documents_status` admits only one
  value. Timestamps needed no coercion layer: both columns are `DateTime(timezone=True)`, so
  the driver returns tz-aware UTC. Coverage 100% line **and** branch on both touched files;
  the db module sits at 96%, the remainder pre-existing and outside this step. Two gaps a
  coverage number cannot see, both checked by hand: the `title` widening produces no branch,
  so the NULL-only arm alone would still have read 100% — it is genuinely pinned by the
  seeded-title test; and the zero-row page has no test here, invisible because an empty
  generator exit is not a reported arc, and it belongs to Scenario 2.3.
- [x] red-adapter rest (the envelope emits every `ProjectItem` field) — `ProjectItemDto` widens
  to the contract's nine fields, timestamps serialized as UTC ISO-8601 with an explicit offset
  (the acceptance DTO's `parse_feed_timestamp` rejects a naive string).
  **Review-pass findings on `6bed7cb0`** (both passes CONCERNS; surfaced, not auto-fixed).
  The fact that sharpens the first three: `GET /api/v1/projects` is **live** — `main.py:150`
  mounts `project_router` and `:182` overrides the provider with the real
  `SqlAlchemyProjectFeedRepository` — so the statement 1.1 is building executes on every
  authenticated call today. These are not "when the feed ships" risks.
  1. *both passes, high/CREDIBLE — the bounded SQL fetch has no owner.* The select now names
     `DocumentModel.content` (`Text`, unbounded) with no `substr` and no `LIMIT`, while
     `ProjectItemDto` still emits `id` alone — so every request materialises the full text of
     every document the caller owns and discards all of it. This is the ADR's own motivating
     cost ("page bytes scale with stored document size") and its Edge Cases table separates the
     two obligations explicitly: "The SQL prefix is a bounded *fetch*; the grapheme-aware trim
     happens in the domain." The deferral list covered the trim and dropped the fetch bound.
     6.2's step list has no `adapter db` step, so nothing schedules it; the trap is that 6.2
     lands the domain-side trim, `preview` is declared correct on the wire, and the SELECT
     stays unbounded forever. Owed: a db test seeding oversized content that pins `preview` is
     already bounded before it reaches the domain — scheduled as itself, at 2.1 with the
     `LIMIT`, not assumed to arrive with 6.2.
  2. *premortem, CREDIBLE — `ProjectPageRequest` is accepted and discarded.* `list_feed` binds
     `request` and never reads it. When 2.1/2.2 widen it with `page`/`limit` (or 3.x with
     `sort`/`q`) before the statement honours them, the parameter arrives populated and is
     dropped in silence — a client paging forever through page 1, answered 200 throughout.
     This commit's own design sets the opposite standard for exactly this shape:
     `MISSING_OWNER_REFUSAL` exists because a forwarded `None` serves "a well-formed, empty 200
     to a caller whose identity was never established". The asymmetry is the finding. Owed:
     `assert_feed_refuses_a_request_it_cannot_honor`, beside the owner refusal.
  3. *premortem, CREDIBLE — no default `ORDER BY`.* Postgres row order is arbitrary and
     unstable in practice (plan flip, an UPDATE relocating a tuple), so the list reshuffles
     between refreshes. 3.x defers the *selectable* order; having a deterministic default at
     all is not the same thing, and the ADR specifies an allowlisted `ORDER BY` plus a
     `(kind, id)` tiebreak. Worse in combination with #2: `LIMIT`/`OFFSET` over an unordered
     statement can show a row on page 1 and page 2, or on neither — a silent drop. Owed before
     2.1 adds paging, not after: a multi-row test pinning the default order and the tiebreak.
     (Every db test today seeds one row per owner by design, so none observes ordering.)
  4. *agent-review, medium — the `title: str | None` widening is enforced by nothing.*
     Dataclasses do not validate annotations, `project_item_shape_statements.py` reflects over
     `field.name`/`field.default` and never `field.type`, and `backend-ci.yml` runs `pytest
     --cov` and no type checker. The seeded-title test pins the *value*, which passes
     identically under `title: str`. Relevant here: at this step the annotation *is* enforced
     (Pydantic), so a narrow `title: str` on `ProjectItemDto` fails at runtime on any untitled
     document rather than at a gate.
  5. *agent-review, low — `_row_of`'s docstring explains why reading the `status` column is
     right and never says the fail-closed-to-`unknown` mapping is still owed.* A reader of the
     function comes away thinking `status` is finished; the CARRIED note lives only in this
     file's prose. One clause at the projection site closes it. Premortem adds the sharper
     half: the guard is a note, not a test, and the day story 1 adds `ready` to
     `ALLOWED_STATUSES` the `ck_documents_status` constraint widens automatically with nothing
     going RED to remind anyone.
  **Checked and dismissed:** premortem's identity-map masking (REMOTE, raised and answered
  twice — `expire_all()` plus the column select, which makes `Row` tuples unanswerable from
  the identity map by construction) and the `title` widening breaking a live consumer (REMOTE
  — no consumer reads it; this step is where `None` first reaches serialization and it is
  written to expect it).
  **How the red landed (2026-08-06):** new
  `rest/tests/router/project/test_project_list_row_serialization.py` (107 lines), one
  whole-body equality of `response.json()` against a hand-written literal. Two seeded rows —
  a titled `document` and an untitled `retryable=True` `generation` — so `title=None` bites
  at the one layer that enforces the annotation (Pydantic), which is finding 4's answer: a
  narrow `title: str` on the DTO raises on the second row rather than passing a value-only
  check. The expectation imports nothing from `ProjectItemDto` and retypes both UUIDs and
  both timestamps by hand, so the mirror defect the db-arm amendment had does not recur.
  Because the comparison is the **whole body**, a `total` back-derived from `len(items)`
  fails here too, and so does a naive timestamp. Predicted `AssertionError: unexpected body
  {'items': [{'id': '1111…'}, {'id': '2222…'}]}` at the body equality with the 200 passing;
  observed exactly that, message identical, so the skip marker carries the real failure.
  **`/test-review` (2026-08-06):** no fixes — all three detectors clean. Placement dismissed
  with a reason worth keeping: the REST tier has **no Statements layer at all**
  (`grep -rn "statements" backend/adapters/rest/tests` is empty); its convention is
  conftest-for-infrastructure plus module-level literals inline, and the one extraction
  precedent (`router/auth/login_router_fixtures.py`) was pulled out only because several
  files shared it. Inventing a REST-only Statements module for one file would break the
  convention, not follow it.
  **Two contract questions, unsettled, for the green:**
  1. `projects_list.yaml` says "UTC ISO-8601 with explicit offset" and does not choose
     between `…Z` and `…+00:00`. The test pins `Z` (Pydantic 2.13's default, verified
     empirically; `datetime.fromisoformat` accepts it on 3.12, so the acceptance DTO's
     `parse_feed_timestamp` holds). The dependency is **loud** — whole-body equality forces
     the green to emit `Z` — but it leaves the spec downstream of the test. Amend the spec to
     name `Z`, or change the literal.
  2. Sub-second precision is unspecified and the dependency is **silent**: both seeded rows
     carry whole-second timestamps, so the test passes whether the serializer preserves
     microseconds or truncates them. Postgres `timestamptz` will carry microseconds in
     practice. Nothing fails loudly to force this one — settle it before green-acceptance.
  **Second file the green must touch:** `test_project_list_router.py:48` asserts
  `{"items": [{"id": str(project_id)}]}` as a whole-body equality by deliberate design (its
  docstring says the scenario adding a field also adds it to these dicts), so it breaks the
  moment the DTO widens. Expected work, not a defect.
- [~] green-adapter rest (the envelope emits every `ProjectItem` field)
  **Review-pass findings on `8c9f567c`** (both CONCERNS; surfaced, not auto-fixed). `/refactor`
  applied nothing — the near-duplicate row constructions ARE the contrast the scenario pins,
  and a conftest assertion helper would replace a working mirror of the sibling file with a
  new abstraction.
  1. *premortem, CREDIBLE — the serializer is never forced to **convert** to UTC, only to
     carry an offset.* `projects_list.yaml` makes two claims, "**UTC** ISO-8601 **with
     explicit offset**", and the whole-body equality pins only the second. Both seeds are
     `tzinfo=UTC` — the identity case for `astimezone(UTC)` — so the test cannot tell a
     normalizing serializer from an echoing one, and Pydantic verifiably echoes: a
     `+07:00` input serializes as `+07:00`, which passes `fromisoformat` and passes "explicit
     offset" while not being UTC. A Postgres session-TZ change (a container without `TZ=UTC`,
     a `PGTZ`, a pooler default) then ships `+03:00` with every backend test green, and the
     frontend's day-grouping is off by the offset. This is a **third** timestamp hole,
     distinct from the two the red recorded: those argue which UTC spelling and how much
     precision; neither asks whether the value is UTC at all. The ADR's edge-case table
     already flags zone-type divergence between the arms, and 1.2 adds a second column.
     Guard: a third seed with `created_at=datetime(2026, 3, 14, 16, 26, 53,
     tzinfo=timezone(timedelta(hours=7)))` expecting `"2026-03-14T09:26:53Z"` — RED on a
     pass-through serializer. (`parse_feed_timestamp` does assert `utcoffset() ==
     timedelta(0)`, but only fires in an environment already misconfigured — after the
     incident, not before.)
  2. *premortem, CREDIBLE — `Cache-Control: no-store` is pinned by nothing, anywhere.*
     `grep -rni "cache-control\|no-store" backend acceptance` returns two hits: the router
     line that sets it (`project_router.py:35`) and the acceptance statements docstring
     explaining why it is deliberately *not* asserted (deferred to 10.6). The header is the
     one item `projects_list.yaml` lists under the 200's `headers:` block, and this step
     rewrites the same handler's return path — a header set by a bare side-effect line above
     the return is exactly what a rewrite drops. The failure class is cross-account
     disclosure via a shared cache. Guard: `assert response.headers["Cache-Control"] ==
     "no-store"` in `test_project_list_router.py`'s envelope test — one line, in a file this
     green already edits, and narrower than pulling 10.6's acceptance assertion forward.
  3. *agent-review, medium — `"retryable": False` does not pin the JSON **type**.* `False ==
     0` in Python, so a DTO declaring `retryable: int` serializes `0`/`1` and the whole-body
     equality still passes. The docstring's claim that a substituted value fails is true for
     eight of the nine fields and false for this one — and it sits precisely in the field the
     commit's own "Pydantic is where the annotation is enforced" argument claims to cover
     (Pydantic *raises* on `title=None` under a narrow annotation, but silently *coerces* a
     bool). Premortem rates it REMOTE because the acceptance DTO already carries
     `assert isinstance(retryable, bool)` with that exact rationale, so an `int` DTO fails at
     green-acceptance. Guard, one line at this tier: `isinstance(row["retryable"], bool)`.
  4. *premortem, borderline — `status` and `kind` reach the wire as unvalidated `str`.* The
     ADR says explicitly they must not be bare `str` ("an unconstrained field is what let the
     fail-closed rule be written for generations only"), and both seeds carry contract-legal
     values, so a `status: str` DTO passes identically. The asymmetry is the finding, not the
     missing mapping: the commit invoked the enforcement-point argument for `title` and
     declined it here. Adjacent to the CARRIED fail-closed rule but not the same ask — a
     constrained DTO field is testable today. Guard: a REST test seeding `status="teapot"`
     asserting the response is not a 200 pass-through.
  **Checked and closed out:** the red's two recorded contract questions are both REMOTE. `Z`
  vs `+00:00` is spec debt — amend `projects_list.yaml` to name `Z`. Sub-second precision
  enforces its own deadline: Pydantic 2.13.4 preserves microseconds and emits a fixed 6-digit
  fraction, never a variable-length one, so green-acceptance goes RED on a mismatch either
  way rather than staying silent.
  **REMOTE, cheap to fold in if this green touches the literals:** the contract says ids are
  unique *within* a kind and instructs clients to dedupe on `(kind, id)`; the two seeds use
  distinct UUIDs, so a two-row test that could have pinned the cross-kind collision for free
  chose not to. Not worth its own step — `list[ProjectItemDto]` is not where it would break.
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

