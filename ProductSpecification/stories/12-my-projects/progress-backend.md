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

---

## Примечание к чекбоксам (2026-08-06)

Функционал ленты, пагинации, сортировки, поиска, `preview` и «Повторить» **написан**, но
вне TDD-цикла — по решению пользователя после мерджа трёх веток в `dev`. Ни один чекбокс
ниже не отмечен задним числом: код без red/green — это код без доказательства, а отметка
`[x]` в этом файле означает пройденный шаг, а не написанную строчку.

Что это значит практически: сценарии 1.2–1.15, 2.1–2.8, 3.1–3.8, 4.1–4.8, 5.1–5.5,
6.1–6.6 и 7.x/8.x по большей части уже **реализованы в коде** и будут проходить свой
red-шаг «зелёными с первого запуска». Это нормальный и ожидаемый исход; честный ход —
написать тест, убедиться, что он зелёный по существу (а не потому, что ничего не
утверждает), и пометить green как `[S]` с указанием, что реализация уже была.

Полный срез возможностей и незакрытых дыр — в `progress.md`.

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
- [x] green-adapter rest (the envelope emits every `ProjectItem` field) — `ProjectItemDto`
  widens to the nine contract fields, `from_domain` forwarding each unchanged; `title` is
  `str | None` (the one layer that enforces it) and `retryable` is `bool`. `ProjectPageDto`
  untouched: no `page`/`limit`/`total`, and its docstring's reason for that still holds.
  `project_router.py` was not touched at all, so `Cache-Control: no-store` is intact.
  The pre-declared second edit landed as expected: `test_project_list_router.py:48` widened
  to the full nine-field row, still one whole-body equality, its docstring corrected to say
  the eight fields are pinned there as *shape* with their contract values pinned next door.
  Coverage 100% line and branch on `project_response_dto.py` (23/23 statements, zero
  branches — a flat declaration plus a nine-argument forward, nothing to branch on); the rest
  module sits at 96% lines / 100% branches, the remainder pre-existing and untouched.
  **The coverage pass ran two mutants rather than trusting the 100%, and both survived:**
  1. `retryable: int` — all 89 tests pass. `json.loads('{"r":0}') == {"r": False}` is `True`,
     so whole-body dict equality cannot tell JSON `false` from `0` in either direction. The
     green reported finding 3 as "closed in production code by the `bool` annotation"; that
     is **wrong** — the declaration is correct behaviour guarded by nothing, and a future
     edit reverting it is undetectable here. Finding 3's one-line `isinstance` guard is still
     owed.
  2. Deleting `project_router.py:35` (`Cache-Control: no-store`) outright — the full rest
     suite stays green. Covered and pinned by nothing; the textbook covered-but-unpinned
     case, now hard evidence rather than an argument. The header is scheduled at the
     acceptance tier by Scenario 10.6, which is much later; finding 2's narrower fix stands.
  **Also surfaced, and it has a scheduled break rather than a hypothetical one:** the widened
  sibling literal carries the `feed_row` fixture's fillers, and two of them are contract-
  *illegal* rather than merely implausible — `"kind": ""` and `"status": ""` are outside the
  enums `projects_list.yaml` declares. The moment finding 4's constrained `status`/`kind`
  field lands, an envelope-*shape* test fails on a validation error that has nothing to do
  with envelope shape. Fix is not "make the fillers plausible": keep them implausible for the
  free-form fields (`preview=""`, `title=""`, epoch timestamps) and make the two enum-shaped
  ones implausible-but-legal (`kind="document"`, `status="ready"`), touching `conftest.py`
  and the router literal. Not a red/green step — it belongs with the amendment below.
  **Adjacent, not scheduled here:** `project_router.py:14`'s `get_list_projects_usecase`
  raises `NotImplementedError` and is never executed, while every auth router has a matching
  `*_di_stub.py` test asserting the un-overridden dependency raises. The project feed router
  has no such sibling — a real inconsistency with the established pattern, belonging to the
  router step rather than the DTO step.
- [x] red-adapter rest amendment (the wire pins what the whole-body equality cannot) — the
  four review-pass findings above, all of which survived a mutant or are structurally
  invisible to dict equality, folded into one red rather than four. Seeds a third row whose
  `created_at` carries a non-UTC offset (`tzinfo=timezone(timedelta(hours=7))`) expecting
  `Z`, so an echoing serializer goes RED where the two identity-case UTC seeds cannot see it;
  adds `isinstance(row["retryable"], bool)` so `False == 0` stops hiding an `int`; adds
  `assert response.headers["Cache-Control"] == "no-store"` to the envelope test, narrower
  than pulling 10.6's acceptance assertion forward; and pins the unknown-`status` behaviour
  as **corrected below**. The enum-legal filler correction already rode along in `bfd11431`.
  **Corrected before the red is written (2026-08-06)** — both review passes on `0ddfb895`
  independently caught that the bullet above originally planned to seed `status="teapot"`
  and assert "the response is **not** a 200 pass-through". That contradicts the contract it
  cites. `projects_list.yaml` says a status the contract does not know "**fails closed to
  `unknown`** — never mapped onto a displayed one", and is "**always present**: an
  implementation that omitted the field on the unknown branch would satisfy a looser schema
  while doing exactly what the fail-closed rule forbids". Fail-closed here means **200 with
  `status: "unknown"`**, not a non-200. Worse, premortem traced where the rejecting reading
  leads: `ProjectItemDto` is constructed per row inside the response path with no per-row
  isolation, and `ProjectPageDto.from_domain` maps the whole tuple — so a `ValidationError`
  on one row reaches `unhandled_exception_handler` (registered as the catch-all in
  `main.py`) and blanks the **entire page** with a 500, for every request, until that row is
  edited. One bad row, one user's whole feed gone. The CARRIED item is the `unknown`
  *mapping*; what is unguarded is the **blast-radius rule** — a per-row problem must never
  become a per-page failure. So the amendment seeds a **two-row** page, row 1 carrying
  `status="teapot"` and row 2 legal, asserting `200`, `len(items) == 2`, and
  `items[0]["status"] == "unknown"`. The original wording would have been satisfied by the
  500 that *is* the failure mode.
  **How the red landed (2026-08-06):** new
  `rest/tests/router/project/test_project_list_wire_contract.py` (178 lines), four tests, three
  skipped `RED:` and one green guard. The three RED failures were observed against an unskipped
  throwaway copy, not argued: `created_at` came back `'2026-03-14T16:26:53+07:00'` for a seed at
  `+07:00` (offset echoed, never converted); the naive seed produced `Failed: DID NOT RAISE
  ValueError`; the `teapot` row came back `'teapot'` where the contract demands `'unknown'`.
  Two offsets are seeded, one east (`+07:00`) and one west (`-05:00`) on `updated_at`, because a
  single eastern seed cannot tell a real conversion from a fixed −7h shift, and because the
  guarantee is "timestamps", not "the first timestamp". The `retryable` test is deliberately NOT
  skipped: the DTO already declares `bool`, so it is a guard over behaviour a surviving mutant
  proved unpinned, and it asserts with `is False`/`is True` rather than `==` or `isinstance` —
  `0 is False` is `False` for a JSON-decoded int, so identity pins type *and* polarity in one
  assertion where `isinstance` would wave through an inverted value. `Cache-Control: no-store`
  landed as one line in `test_project_list_router.py`'s envelope test, as scheduled.
  **`/test-review` (2026-08-06):** two fixes. (1) All three per-field assertions became whole-row
  list equality, so a green that converts the timestamps or maps the status while corrupting one
  of the other eight fields now fails; the `retryable` test keeps its identity reads *in addition*
  to equality, since dict equality is structurally incapable of seeing a JSON `0`. Re-verified
  after widening: each diff still isolates the one guarantee its test names, so the RED did not go
  ambiguous. (2) `pytest.raises(match="created_at")` → `match=r"created_at must be timezone-aware"`
  — the message decided now rather than deferred to the green, left unanchored so it holds whether
  a hand-rolled validator or Pydantic's `Value error, …` envelope carries it. The row builders
  moved into `conftest.py` (`contract_row`/`expected_row`, with `feed_row` now delegating to
  `contract_row`): the whole-row expectations had pushed the file past the 200-line limit, and the
  move leaves exactly one `ProjectItem` construction site in the directory, so a tenth contract
  field is added in one place. Dismissed: the repeated usecase-double assembly (real duplication,
  zero strictness effect — handed to `/refactor`); the `RED:` markers (this repo's convention); the
  absent REST Statements tier (settled at the previous step); and binding `_row`'s defaults to the
  sibling's expectation literal, which would make one code path of both sides of that equality.
  Tests: 90 passed, 3 skipped (rest module).
- [x] green-adapter rest amendment (the wire pins what the whole-body equality cannot) —
  expected shape: a tz-aware-guarded `astimezone(UTC)` field serializer, and a `status`/`kind`
  treatment that **maps** an unknown value to `unknown` rather than rejecting it (see the
  correction above — a constrained `Literal`/`Enum` field that raises is the outage, not the
  guard). Record at the green which mechanism carries the mapping, because the ADR requires
  the *document* arm to fail closed too.
  **Two further findings from the `0ddfb895` passes, to settle here:**
  1. *agent-review — the naive-timestamp case is worse than uncovered, and the planned fix
     would hide it.* The DTO docstring says timestamps serialize with an explicit offset,
     "Pydantic's default form for a **tz-aware** `datetime`" — the qualifier is load-bearing
     and unflagged. A naive value serializes `"2026-01-01T12:00:00"`, offset-less, which
     `parse_feed_timestamp` would at least catch. But `astimezone(UTC)` **does not raise** on
     a naive datetime: Python assumes system local time, so the planned serializer converts a
     visible contract violation into an invisible one — a well-formed `Z` string naming the
     wrong instant, shifted by the deploy host's offset, passing in a UTC container and wrong
     on a developer machine. The ORM columns are `DateTime(timezone=True)` so the ordinary
     path is aware; the feed is a hand-written cross-table projection, which is exactly where
     awareness gets dropped. The serializer must be `astimezone` **guarded by a naive
     rejection**, and the red should seed a naive row expecting that rejection.
  2. *agent-review, low — the `retryable` docstring claims an inbound strictness the field
     does not have.* "Declared `bool` rather than left to coercion" describes `strict=True`;
     the plain declaration coerces `1`/`0`/`'yes'`/`'no'` happily and raises only on `2` or
     `'maybe'`. The sentence's narrow claim (an `int`-typed field would *emit* `0`/`1`) is
     true, but the framing will be trusted later — the commit message repeats it verbatim.
     Note that the scheduled `isinstance` guard pins the **wire** type and would not catch
     this.
  **Checked and dismissed:** `extra='forbid'` on either DTO (agent-review, minor — the
  router test's docstring justifies its whole-body equality by saying an invented field must
  fail, and Pydantic's default `extra='ignore'` silently drops a stray keyword instead, so
  the guard is one-directional; real, but out of altitude for the DTO step).
  **The unbounded-preview finding is now a wire concern, not a storage one** (premortem,
  CREDIBLE). It was raised against `6bed7cb0` as "the bounded SQL fetch has no owner": the db
  arm selects `DocumentModel.content` whole and `_row_of` sets `preview=row.content`
  verbatim. Until this step that died at the DTO boundary, because `ProjectItemDto` carried
  `id` alone. `0ddfb895` is the line that puts it on the wire. Two costs, one line: the page
  payload now grows as *rows × full document size*, which is what the contract forbids in as
  many words ("Read as a bounded prefix in SQL, so the bytes a page reads do not grow with
  stored document size"), with no `LIMIT` and no 3 s `QUERY_TIMEOUT`/503 backstop
  implemented; and every document's **full body text** now leaves the server on a *list*
  endpoint — into browser memory, client error-reporting payloads, and any proxy that samples
  bodies. The contract's "bounded prefix" wording is a confidentiality choice, not only a
  size one. 6.2 and 6.3 own the preview *derivation*; nothing owns the *bound*, and the
  route is live. Owed, and not covered by the amendment above: a db statement test seeding
  ~5 000 code points asserting `len(preview) <= 200` and that the compiled statement selects
  a bounded expression, plus the matching wire assertion here. Grep confirms neither exists
  at any tier today.
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
  **Review-pass findings on `ca62dbc9`** (both CONCERNS; surfaced, not auto-fixed). `/refactor`
  applied two changes — a `feed_serving(*rows)` conftest fixture collapsing the character-identical
  usecase-double assembly at 6 of 7 sites (the 401 test keeps its bare `AsyncMock()`, since handing
  it a `ProjectPage` would install the page it exists to prove is never fetched), and a corrected
  `contract_row` docstring, which had falsely claimed to be the directory's single `ProjectItem`
  construction site. It declined routing the row-serialization module's literals through the
  builders: that scenario earns "every field reaches the wire" by holding a hand-written domain row
  and its hand-written wire form side by side, and sourcing both from conftest would make it assert
  that conftest agrees with conftest. Flagged: `conftest.py` is at 188/200 — the next fixture must
  split it (infrastructure fixtures vs row builders), not append.
  1. *both passes, high/CREDIBLE — the naive-timestamp refusal is the whole-page outage this very
     file forbids two tests later.* `test_should_refuse_a_naive_timestamp_rather_than_shift_it`
     asserts `pytest.raises(ValueError)` and nothing about the wire. It escapes only because the
     test harness's `project_app` registers a handler for `ValidationException` alone; `main.py:161`
     registers `unhandled_exception_handler` for bare `Exception`, so in production one naive
     `created_at` on one row returns 500 for that caller's **entire feed**, on every request, until
     the row is edited. The status test seeds two rows and asserts `len(items) == 2` under the
     docstring "a per-row problem must never become a per-page failure"; the timestamp branch is
     held to the opposite rule with no argument for the asymmetry. The refusal itself is defensible
     (the ADR rejects naive columns at the schema) — what is unguarded is the blast radius. Owed at
     the green: seed the naive row on a **two-row** page and assert what the caller actually
     receives, then make the refuse-the-row vs refuse-the-page choice deliberately.
  2. *agent-review, medium — the naive refusal is pinned for `created_at` only.* `match=r"created_at
     must be timezone-aware"` plus a naive seed on that field alone. A green guarding `created_at`
     and running a plain `astimezone(UTC)` on `updated_at` passes all four tests and reproduces on
     `updated_at` exactly the invisible wrong-instant shift the docstring describes — the same
     first-timestamp-only asymmetry the conversion test seeds two opposite offsets to close.
  3. *both passes, high/CREDIBLE — the contract's log signal on the unknown branch is guarded by
     nothing.* `projects_list.yaml` says an unknown status fails closed to `unknown` "**and emits a
     log signal carrying the id and the unrecognized value**". The RED pins the mapping and the
     surviving row count and drops the clause; its docstring paraphrases the contract line minus
     that half. `grep -rn "caplog\|logger"` over the project rest tests and DTO is empty. Fail-closed
     without a signal is fail-**silent**: the day a new status ships, rows render `unknown`, no error
     rate moves, and nobody can say when it started. Owed: a `caplog` assertion in the test that
     already exists.
  4. *premortem, CREDIBLE — the legal direction of the status enum is pinned by nothing.* The green
     must introduce a known-status set in REST — a second copy of the contract's eight-member enum —
     and across the whole rest suite only `ready` and `failed` ever cross the serializer. An
     allowlist short by `draft`, `pending`, `in_progress`, `completed` or `recovering` passes 90/90
     while rendering every in-flight generation as `unknown`. Not hypothetical: a real
     `ALLOWED_STATUSES = ("draft",)` already exists in the db layer. Owed: a parametrize over the
     eight yaml enum members asserting each reaches the wire unchanged.
  5. *premortem, CREDIBLE — sub-second precision, again, and this time with a mechanism.* Every
     datetime literal in the entire rest suite has `microsecond=0`; Postgres `timestamptz` does not.
     `strftime("%Y-%m-%dT%H:%M:%SZ")` and `isoformat().replace("+00:00","Z")` agree on every fixture
     and disagree on real data. The red reached hard for one blind spot in these literals (both
     seeds UTC) and walked past its neighbour in the same lines. Owed: one seed with a nonzero
     microsecond, pinning its wire form. (This supersedes the "settle it before green-acceptance"
     note above — settle it here.)
  6. *agent-review, low-medium — the one unskipped test seeds a contract-illegal row.*
     `contract_row(_ID_TWO, status="failed", retryable=True)` keeps the default `kind="document"`,
     and the contract makes `retryable` true only for a failed **generation**. Same class of fixture
     illegality `bfd11431` went out of its way to remove, in a fixture whose docstring now promises
     legality by name. One keyword: `kind="generation"`.
  7. *agent-review, low — the `Cache-Control` assertion cannot render its own failure message.*
     `response.headers["Cache-Control"]` raises `KeyError` before the assertion evaluates, so the
     exact mutant it was written to catch (deleting the router line) reports a `KeyError` rather
     than the message. Use `.get(...)` in the assertion itself.
  **Rated REMOTE:** `Cache-Control` absent on 4xx/5xx (the contract names it only under the 200, and
  error bodies are not per-account content); `contract_row`/`expected_row` drift as a tenth field
  lands (a dropped field fails the whole-row equality loudly); the conversion test's seeds landing
  exactly on `expected_row`'s defaults (editing conftest breaks it loudly, not silently).
  **Coverage pass on the amendment green (2026-08-06):** `project_response_dto.py` is at
  **100% line and 100% branch** — no uncovered line, no half-taken branch. The number is not
  the finding. Two mutants the suite does not kill, both of them the `ca62dbc9` premortem's
  findings 4 and 5 still standing after the green that was supposed to settle them:
  1. **Five of the eight statuses are pinned by nothing.** Rewriting a `ProjectStatus` member's
     value so the contract's spelling no longer resolves — i.e. simulating an allowlist short
     by that member — leaves the suite green for `DRAFT`, `PENDING`, `IN_PROGRESS`, `COMPLETED`
     and `RECOVERING` (93 passed each). Only `READY` (5 failures) and `FAILED` (2) are held.
     `_fail_closed_to_unknown` is what hides them: a missing member does not raise, it renders
     `unknown`, so a too-narrow enum is indistinguishable from a correct one at every tier
     below acceptance. The fail-closed rule and the enum's legal direction must be tested
     together — the first one silences the second.
  2. **Sub-second precision is unpinned.** Appending `.replace(microsecond=0)` to `_as_utc`'s
     return — a truncating serializer — leaves all 93 green, because every datetime literal in
     the rest suite has `microsecond=0` and Postgres `timestamptz` does not.
  Mutants that *are* killed, recorded so they are not re-litigated: dropping `astimezone(UTC)`
  (1 failure), dropping the naive guard (1), guarding/converting `created_at` while leaving
  `updated_at` a pass-through (1 — finding 2's asymmetry is genuinely closed), and unrecognising
  either `ProjectKind` member (5 and 1) or `UNKNOWN`'s own wire value (1).
  Still unguarded and *not* a coverage gap in this file, so no step below: the contract's log
  signal on the unknown branch (finding 3) — `_fail_closed_to_unknown` emits none and
  `grep -rn caplog` over the project rest tests is still empty.
  **How the green landed (2026-08-06):** all three skips removed, all three pass; 93 passed /
  0 skipped in the rest module, 721 passed / 2 skipped whole-backend, no regression. Two
  `StrEnum`s land in the DTO module — `ProjectKind` (`document`|`generation`) and
  `ProjectStatus` (the contract's eight values, `unknown` among them) — so neither field
  reaches the wire as a bare `str`, per the ADR; `StrEnum` members serialize to their value,
  so the wire form is unchanged for legal input.
  **The mechanism carrying the unknown-status mapping** (recorded because the ADR requires the
  *document* arm to fail closed too): a `@field_validator("status", mode="before")` named
  `_fail_closed_to_unknown`, doing `ProjectStatus(value)` and returning `ProjectStatus.UNKNOWN`
  on `ValueError`. It is **kind-agnostic** — it sits on the single DTO both UNION arms serialize
  through and branches on nothing, so the document arm fails closed exactly as the generation arm
  does, which is the ADR's edge-case row (`ALLOWED_STATUSES = ("draft",)` today against a
  contract that can emit `ready`). It is a `before` validator rather than a translation inside
  `from_domain` because the router declares `response_model=ProjectPageDto` and FastAPI
  **re-validates** the returned model — a `from_domain`-only mapping would be undone by that
  second pass. Being a mapping and not a rejection, it cannot raise into `main.py`'s catch-all,
  so one bad row cannot blank the page; the two-row assertion is what confirms it.
  Timestamps: `@field_validator("created_at", "updated_at")` `_as_utc` rejects a naive value
  (`tzinfo is None or tzinfo.utcoffset(value) is None`) with
  `ValueError(f"{info.field_name} must be timezone-aware")` **before** `astimezone(UTC)` — the
  guard is not redundant with the conversion, since `astimezone` silently reads a naive value as
  host-local time. The field name comes from `ValidationInfo.field_name`, so `updated_at` names
  itself; the coverage pass then killed the mutant that guards `created_at` alone, so finding 2's
  first-timestamp-only asymmetry is genuinely closed rather than argued.
  **Two obligations the green identified and deliberately did not perform**, both needing tests a
  green may not write: (a) the ADR places `ProjectStatus`/`ProjectKind` in the **domain**, and they
  are defined in the REST DTO module — `ProjectItem.status`/`.kind` are still bare `str`, and
  moving the enums inward has no failing test driving it; (b) the contract's log signal on the
  unknown branch is still unemitted, and a `before` validator cannot see sibling fields, so the
  row id is not reachable from where the mapping happens — the emission will likely have to live
  in `from_domain` (which holds the whole `ProjectItem`) while the mapping stays in the validator.
  **Judged, not overlooked:** `ProjectKind` has no fail-closed member, so an unrecognised `kind`
  **will** raise and blank the page — the failure mode the status test exists to forbid. Held to
  be correct: the contract declares no `unknown` kind, and `kind` is the adapter's own
  discriminator over two hard-coded UNION arms, not stored data a migration can widen. Recorded in
  the class docstring so a later disagreement has something to argue with.
- [~] red-adapter rest (coverage: every contract status reaches the wire unchanged)
- [ ] green-adapter rest (coverage: every contract status reaches the wire unchanged)
- [ ] red-adapter rest (coverage: nonzero microsecond survives serialization)
- [ ] green-adapter rest (coverage: nonzero microsecond survives serialization)
- [ ] red-adapter rest (the unknown branch signals, and a naive row costs one row not the page) —
  the three `ca62dbc9` review findings the amendment green could not carry, since each needs a
  test. (i) The contract's `status` clause has two halves and only one is built: an unrecognised
  value must also "emit a log signal carrying the id and the unrecognized value" — a `caplog`
  assertion on the existing two-row unknown test, plus the production move the green named (the
  emission in `from_domain`, which holds the whole `ProjectItem`, while the mapping stays in the
  `before` validator that cannot see the id). (ii) The naive-timestamp refusal is asserted only as
  `pytest.raises`, which observes the exception escaping `ASGITransport` and nothing about the
  served response; in production it lands in `main.py:161`'s catch-all and returns 500 for that
  caller's **whole feed**, on every request, forever — the exact blast radius the status test two
  functions later forbids in as many words. Seed the naive row on a **two-row** page and assert
  what the caller actually receives, which forces the refuse-the-row vs refuse-the-page choice to
  be made rather than inherited. (iii) Two test-hygiene fixes that must ride a red because they
  touch tests: `contract_row(_ID_TWO, status="failed", retryable=True)` keeps the default
  `kind="document"` and the contract makes `retryable` true only for a failed **generation** — the
  same fixture illegality `bfd11431` removed, in a fixture whose docstring now promises legality;
  and `response.headers["Cache-Control"]` raises `KeyError` before its own assertion message can
  render, defeating the very mutant it was written to catch (use `.get(...)` inside the assertion).
  **Review-pass findings on `579fe401`** (both CONCERNS; surfaced, not auto-fixed). They converge
  on one question this red must answer explicitly rather than inherit: **is the fail-closed unit
  the `status` field, or the row?** Every finding below is a different way the field-level answer
  leaks. `/refactor` applied one behaviour-preserving change only — hoisting a repeated
  `response.json()["items"]` decode into a local — and then died on an API error; the tree was
  verified clean and the whole backend re-run green before the commit.
  1. *both passes, medium/CREDIBLE — `_fail_closed_to_unknown` swallows every input, not only
     unrecognised status **strings**.* `Enum.__call__` raises `ValueError` for any non-member, so
     `None`, `123`, `True`, `['ready']`, `b'ready'` and `object()` all render `unknown` (agent-review
     ran each against the real DTO). The contract's clause is narrower — "a *status* this contract
     does not know" — and a `None` from a NULL column, a not-yet-backfilled migration or a
     LEFT-JOIN miss on the generations arm is a **projection bug**, not an unknown status. They are
     now indistinguishable on the wire, and the branch that swallows both emits nothing. Premortem's
     blast radius is the sharp half: a schema-level cause hits every row of every account at once
     and returns 200 carrying plausible JSON — the one shape no error-rate monitor catches. This
     also undercuts `ProjectItemDto`'s own docstring claim that this is "the layer where that
     widening is *enforced* rather than merely declared": for `status`, it now enforces nothing.
     Owed: a seed with `status=None` asserting a distinguishable outcome (a refusal, or at minimum
     a distinct signal), and a narrowed `except` so one predicate serves both the mapping and the
     scheduled log emission instead of `from_domain` re-deriving it and drifting.
  2. *premortem, CREDIBLE — an unknown-status row still reaches the wire `retryable: true`.*
     `from_domain` forwards `retryable` verbatim while `status` is normalized, so
     `(status="teapot", retryable=True)` serializes as `{"status": "unknown", "retryable": true}` —
     a combination `projects_list.yaml` forbids ("true only for a `failed` generation…; offering a
     retry on a pending/in_progress/recovering row would duplicate work that is still running").
     A row whose status the contract cannot resolve is by construction not a known-`failed`
     generation. Fail-closed on one field with pass-through on its dependent field is not
     fail-closed. Unreachable today only because the documents arm pins
     `_DOCUMENTS_ARE_NEVER_RETRYABLE = False`; live at 1.2/1.3, and this commit is what makes
     `unknown` a value that arm can produce. Owed: seed
     `contract_row(kind="generation", status="teapot", retryable=True)` and assert
     `items[0]["retryable"] is False`. Note the existing unknown test is satisfied by pass-through
     because its seed keeps the default `retryable=False`.
  3. *premortem, CREDIBLE — the `ProjectKind` no-fail-closed judgement is a claim about today's SQL
     that nothing tests.* An unrecognised `kind` raises into `main.py`'s catch-all and blanks the
     page — the outage the neighbouring status test exists to forbid. The judgement (recorded in the
     class docstring, and independently verified sound for the arm that exists: no `documents.kind`
     column, `_DOCUMENT_KIND` a SQL-side literal) rests on there being exactly two hard-coded arms.
     A typo in the second arm's literal, or a third arm, is a full-page 500 with a green suite.
     Owed: name `kind` explicitly in this step's isolation scope — a per-*field* refusal decision
     made for timestamps will not cover it — or a storage-adapter test asserting every `kind` the
     repository can emit is a `ProjectKind` member.
  4. *agent-review, low — `_as_utc`'s naive guard is bypassed by a numeric timestamp.* The guard
     reads `value.tzinfo`, i.e. only what Pydantic already coerced, and lax mode turns an
     `int`/`float` into a tz-aware UTC datetime, so `created_at=0` satisfies it by construction. A
     naive *string* is correctly refused, so the string path is sound; `ProjectItem.created_at:
     datetime` is an unenforced dataclass annotation, so nothing upstream rules the numeric path
     out. Low — no producer emits one — but it is a second route to the laundered-wrong-instant the
     docstring exists to prevent.
  5. *agent-review, low — the diff ships both sides of an argument it also states.*
     `_fail_closed_to_unknown`'s docstring argues at length that a per-row problem must never
     become a per-page failure; `_as_utc` then does exactly that, and the class docstring blesses
     it. Worth recording that the choice this step is scheduled to "make rather than inherit" is
     already asserted in both directions in shipped code.
  6. *agent-review, low — `ProjectItemDto`'s docstring says "all nine fields `projects_list.yaml`
     declares required"; the `required` list has **eight** (`title` is excluded, as the same
     docstring states two sentences later). Pre-existing text, but this commit rewrote the
     paragraph below it and left it standing.
  **Checked and clean, recorded so it is not re-litigated:** `ProjectStatus`'s eight members match
  the contract enum member-for-member; `StrEnum` makes both validators idempotent under FastAPI's
  `response_model` re-validation, and would fail the sibling whole-row equality if it changed the
  wire form of a legal value; unhashable `status` input escapes as `ValueError`, not `TypeError`,
  so the `except` holds.
- [ ] green-adapter rest (the unknown branch signals, and a naive row costs one row not the page)
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

### Scenario 1.12 A conversion committing during the read is still counted once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.13 A generation converted before the document link existed does not appear twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.14 A completed generation whose conversion failed is a retryable feed item
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.15 One arm failing fails the whole request
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

### Scenario 2.8 An insert during paging skips at most one item
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

### Scenario 3.8 Ordering is total when a document and a generation collide on both key and id
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

### Scenario 4.8 Changing the sort under an active search returns the same set from its first page
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

### Scenario 7.5 Retrying a generation that has since become a document is refused with its current status
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

### Scenario 8.15 A source whose retry already succeeded can be retried again
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

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

### Scenario 4.1 Retry Reaching the Model Provider — a retry produces a real generation with the source's parameters
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2 A retry whose provider call fails leaves a failed generation, not a lost one
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3 A retry whose provider call times out does not hang the request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1 A document created from a generation replaces it in the feed
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

### Scenario 2.2 Wildcards cannot widen the search
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2 A preview cut from stored markup cannot reopen a tag
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3 The echoed search query renders as text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2 Server-owned list fields cannot be supplied by the caller
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

### Scenario 2.3 Abandoned searches do not accumulate
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

### Scenario 3.3 A database without the pinned collation is rejected at startup
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4 The search deadline does not outlive its request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

