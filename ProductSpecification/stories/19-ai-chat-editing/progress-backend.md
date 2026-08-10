# Story 19: AI chat editing of an existing document (SSE, revisions, rollback) — Backend Progress

Bootstrapped from the test spec on 2026-07-29. Owns: Backend, Integration, Security, Load
and Infrastructure Scenarios (acceptance steps stay inline per scenario — they aren't a
separable layer). Frontend scenarios live in `progress-frontend.md` — never edited from
this session. Narrative, decisions and the Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

The backend test spec is split across several files (see the Decisions section of
`progress.md`); each file gets its own section below, and scenario numbers are unique
within their file, not across the story.

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1: Every endpoint refuses an absent document indistinguishably from a foreign one
- [x] red-acceptance — 7 endpoints parametrized, 7 failed then class-level skip marker. `/test-review`
      found every assertion was satisfied by Starlette's fallback 404; both probe bodies are now pinned
      to the canonical `{"error_code": "NOT_FOUND", "message": ...}` envelope, so byte-identity rests on
      an anchor instead of on mutual agreement. green-acceptance must raise `NotFoundException` and let
      the existing handler answer — a bare `HTTPException(404)` renders `{"detail": ...}` and fails.
      "No edit is created" is verified indirectly via the owner's `GET /messages` (spec §3.1 coupling)
      plus a whole-body `GET /documents/{id}` compare as the positive control.
- [x] design — Option B′ chosen, ADR at `decisions/document-scope-guard-decision.md`. Hazard scan
      covered all 8 `_index.md` groups; 37 GAPs, 30 owned by other already-specified scenarios,
      7 folded into this design as forced guards (bounded projection, write-side predicates,
      404-before-409/422 ordering, non-streaming stream refusal, mutation suppression, zero
      quota/queue effect, no foreign id in logs).
- [x] red-usecase — one test on `resolve_owned_document`, skipped at class level. `/test-review`
      found the refusal identity was asserted *relatively* (`str(foreign) == str(absent)`), which the
      house style at `save_document.py:96` would have satisfied while leaking the id; both refusals are
      now pinned to the literal `REFUSAL_MESSAGE = "document not found"`, so the message must be
      written to that string. The bounded projection is pinned by field name (`["id", "owner_id"]`) —
      a later `content` field with a default would otherwise pass dataclass equality silently. Seeding
      goes through the real `CreateDocument` usecase, not a hand-built row. `version` is deliberately
      **not** on `DocumentScope` yet (the ADR lists it): no Statements line reads it until the
      base-version scenarios 2.x, and the domain field gate forbids an unread field. Add it there.
- [x] green-usecase — `resolve_owned_document` raises one id-free `NotFoundException("document not found")`
      for both the absent and the foreign case. The read goes through a **new bounded port method**
      `DocumentRepository.find_scope_by_id_and_owner -> DocumentScope | None` rather than a slice of
      `find_by_id_and_owner`: the ADR rejects "resolver returning the full `Document`" because the
      200 000-unit `content` is paid at the SELECT, so projecting after the load would implement the
      rejected option while passing the test. `DocumentScope` moved to its own module (the port must
      name it in a signature; importing from the guard module would be circular). `FakeDocumentRepository`
      projects; the **db adapter has no `find_scope_by_id_and_owner` yet** — deliberately left for
      adapters-discovery. `/test-coverage usecase --focus`: 100% lines and branches on all three new files.
- [x] adapters-discovery — Check 1 (ports): **db** — `SqlAlchemyDocumentStorage` has no
      `find_scope_by_id_and_owner`, and because it satisfies `DocumentRepository` structurally
      rather than by inheritance the gap is invisible at import and at construction; only mypy
      sees it, and mypy runs nowhere (`backend-ci.yml` is pip/alembic/pytest). It is red **today**
      on four already-shipped wiring sites (`document_wiring.py:17,25,30,36`). Check 2 (exceptions):
      **rest** — `[S]`, `not_found_exception_handler` already maps `NotFoundException` to 404
      `{"error_code": "NOT_FOUND", "message": ...}`, the exact envelope the acceptance probes pin.
      Check 3 (response shape): **rest** — none of the seven AI-edit routes exist (`router/` holds
      only `auth`, `document`, `generation`), which is what the acceptance disable marker says: a
      refusal cannot be told apart from an unrouted request.
- [x] red-adapter db — 4 tests against the real Postgres schema, skipped at class level; all four
      fail with `AttributeError: 'SqlAlchemyDocumentStorage' object has no attribute
      'find_scope_by_id_and_owner'` when the marker is lifted. The absent-id case seeds a document
      **for the asking owner** and then asks for a different id, so an `owner_id`-only predicate (or
      a finder that echoed its arguments back as a scope) fails there; the foreign case seeds under
      someone else, so an `id`-only predicate fails there — each predicate is held by the case that
      can move without it. `/test-review` found the projection expectation was derived from
      `dataclasses.fields(DocumentScope)`, i.e. a test that widens with the DTO it guards: it is now
      the literal `["id", "owner_id"]`, matching the usecase side at
      `document_scope_guard_statements.py:30`, and compared order-insensitively (`SELECT owner_id, id`
      is a correct green). The content check is one compound step,
      `assert_the_scope_was_resolved_without_reading_content` — split in two it was satisfiable by a
      finder that emits one cheap non-content SELECT and returns `None`. SQL capture lives in a new
      `statements/sql_recorder.py` listening on the **sync** engine (a listener on the `AsyncEngine`
      never fires, and zero recorded statements reads as "no `content` was selected").
      **Known duplication:** `test_document_storage_cas_shape.py` and
      `test_generation_storage_cas_shape.py` each hand-roll the same recorder — fold both onto
      `recording_sql` once this is green (they'd also gain the strict projection parsing).
      *(Stale as of 2026-07-31: both already import `recording_sql` and share
      `statements/cas_shape_statements.py`; `grep before_cursor_execute` across `backend/` returns only
      `sql_recorder.py`, so one recorder implementation exists. The fold happened at that green step and
      the note was never updated — do not pick it up as open work. The "strict projection parsing" half
      never applied: those two use `starting_with()` for statement-verb counting, a different guard.)*
- [x] green-adapter db — `find_scope_by_id_and_owner` is `select(DocumentModel.id, DocumentModel.owner_id)`,
      a **column projection** rather than `select(DocumentModel)` sliced afterwards, with both `id` and
      `owner_id` in the WHERE — so the recorder's `["id", "owner_id"]` assertion holds at the SQL, not at
      the DTO. 4/4 db tests green, full backend suite 509 passed. The silent-failure shape is closed on
      both sides: the six `DocumentRepository` Protocol bodies now `raise NotImplementedError` (a `...`
      body is a concrete coroutine returning `None`, i.e. an unimplemented port refuses every owner their
      own document), and `backend-ci.yml` gained a mypy step — `mypy==1.19.0` and the `pyproject.toml`
      config both already existed and nothing was running them. `/test-coverage db --focus`: 100% lines
      and branches on `document_storage.py`. Two findings worth carrying:
      (a) the tech template's coverage command omits `--cov-branch`
      (`.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:9,14`), so every past
      "100% branch coverage" report from it measured nothing;
      (b) this is now the only 1 of 17 usecase Protocol ports using `raise NotImplementedError` — the
      other 16 still use `...`. The split state is the worst of both; decide once, project-wide.
      **Environment:** the default `textery` database can no longer migrate on this branch
      (`Can't locate revision identified by 'a3b4c5d6e7f8'` — a newer branch migrated it). A clean
      `textery_s19` database now exists in the same `infra-postgres-1` container; point
      `TEST_DATABASE_URL` there for db-layer runs.
      **Review-pass follow-ups (non-gating, both CONCERNS):**
      (1) `FakeDocumentRepository` (`usecase/tests/statements/document_fakes.py`) is a bare class,
      never bound to `DocumentRepository` — and mypy does not check unannotated test bodies
      (`check_untyped_defs` is unset; turning it on today reports 30 latent errors). So the fake can
      drift from the port with the usecase suite fully green, which is the same silent shape this step
      closed on the adapter side. Cheapest fix: a module-level `_conforms: DocumentRepository =
      FakeDocumentRepository()`.
      (2) `backend-ci.yml` triggers only on `push: [main, dev]` and `pull_request`; this project uses
      neither — work lands directly on the feature branch. The mypy step therefore does not run until
      the story merges, i.e. after all seven endpoints it was added to protect. Widen the trigger.
      (3) `DocumentScope` carries no `version`, but the write path is
      `save_content_if_version_matches(expected_version=…)` — so the next endpoint author's cheapest
      move is a second, full-entity `find_by_id_and_owner` right after the guard, reading `content`
      after we paid to avoid it. The ADR already lists `version` on the scope; add it at scenario 2.x
      as planned, and consider a usecase-level no-`content`-SELECT assertion (the recorder guard
      exists only at the adapter layer today).
- [x] red-adapter rest — 5 test methods, **37 parametrized items**, class-level skip marker; all 37
      fail with `b'{"detail":"Not Found"}'` vs the canonical bytes (30) and `await_count 0 == 1` (7).
      The production side is a router stub: seven providers, zero handlers.
      `/test-review` found both of this scenario's recurring weaknesses still live. Byte-identity was
      a `set()` cardinality check — seven routes that don't exist return the same bytes every time, so
      it passed for exactly the state the scenario rules out; it is now seven independent equalities
      against a `CANONICAL_REFUSAL_BYTES` literal (identity follows transitively, and a failure names
      the diverging route). The stream test was worse: unskipped, **3 of its 4 assertions passed
      against the missing route** — `headers.get("content-type", "")` let an *absent* header satisfy
      the negative check, and `startswith("application/json")` admits `application/json-seq` and
      `application/jsonlines`, both streaming types. Exact content-type now, on all seven routes.
      Kwargs were `str(kwargs.get("document_id")) == document_id`: `.get()` degraded a missing kwarg
      to `str(None)`, and `str()` accepted the raw path string or anything whose `__str__` matched —
      now typed and structural, with the child identifiers (`edit_id`, `revision_number`) asserted
      for the first time. Coverage widened 21 → 37: resolve-before-validate ran against the queue
      route only, but `CANCEL_EDIT` and `RESTORE_REVISION` are equally free to declare a validated
      body model FastAPI answers 422 from before the guard runs.
      **Two constraints green must respect:** (1) the body-carrying routes cannot declare a Pydantic
      body model as a handler parameter — FastAPI validates it before the handler body runs, so a
      malformed `base_version` would 422 before `resolve_owned_document` is reached; accept the body
      raw and validate *after* the guard, or hang validation off a dependency ordered behind it.
      (2) the stream route must `await` the usecase **before** constructing the response —
      `StreamingResponse(generator())` with a raise inside the generator commits a 200
      `text/event-stream` status line before the guard's answer is known.
- [x] green-adapter rest — seven handlers on the existing seven providers, each one statement:
      path identifiers typed by FastAPI, owner id from `Depends(get_current_owner_id)`, awaited on
      the route's usecase with `(document_id, owner_id)` plus the child identifier where the route
      has one. No policy in the controller — the guard stays the usecase's first statement and the
      refusal is rendered by the app's existing `not_found_exception_handler`. Both red-phase
      constraints hold at the code, not by luck: (1) **no route declares a Pydantic body parameter**,
      so FastAPI has nothing to validate before the handler body runs — all 15 resolve-before-validate
      items (3 body-carrying routes × 5 disclosing bodies) reach the usecase with `await_count == 1`;
      (2) `stream_ai_edit` awaits the usecase and returns its result directly — **no
      `StreamingResponse` at all**, so no 200 `text/event-stream` status line can be committed before
      the guard answers. 37/37 rest items green, full backend suite 546 passed.
      `/test-coverage rest --focus` (with `--cov-branch` added by hand — the tech template still omits
      it, see line 83): 34/41 lines, 0/0 branches — every handler is a single `return await`, so the
      zero branch total is the design. The 7 uncovered lines are the DI provider stubs
      (`raise NotImplementedError`), reachable and load-bearing; the coverage pair below pins them
      following the `auth` precedent (`test_login_post_router_di_stub.py` asserts the exact message,
      not merely the type). The same stub gap exists untested in `document_router.py` (4 lines) and
      `generation_router.py` (1) — out of this scenario's scope, but they are the entire remainder
      between `adapters/rest` and 100%.
      **Carry into 2.x:** minimality means the body-carrying routes read **no** request payload today —
      `message` / `base_version` / `revision_number` are not yet on the wire contract. When 2.x adds
      them the payload must be read *after* the guard (raw body, or a dependency ordered behind it),
      never as a declared model parameter; the module docstring says so at the point where the
      mistake would be made.
- [x] red-adapter rest (coverage: seven AI-edit DI stubs raise NotImplementedError) — a **legitimate
      no-red**: the stubs this pins were already written in `d553f2d`, so the test passed on its first
      run (7 passed) and no marker was re-applied — a passing coverage test left skipped covers nothing.
      Predicted "none / 7 passed", actual "none / 7 passed". Follows the auth precedent
      (`test_login_post_router_di_stub.py`): direct module import, **not** `importorskip` — this test *is*
      the composition-root guard and must fail loudly if the module stops importing. The message is
      asserted against the string **literal**, never the module's `_WIRED_BY_COMPOSITION_ROOT` constant,
      which would make the assertion tautological. `/test-review` found the provider roster was a
      hand-transcribed snapshot: an eighth `get_*_usecase` stub added later would be invoked by no test
      and stay silently uncovered — the same gap one level up from the one the test closes. The roster is
      now discovered from the module (`dir()` filtered to `get_*_usecase`) and pinned against seven
      literal names in `test_should_expose_exactly_the_seven_known_providers`; parametrize cases come
      from a `name -> route` dict, so the provider/id pairing is structural rather than two hand-ordered
      parallel lists. Router coverage 41/41 lines, 0 missed. Full rest suite 116 passed.
      **Housekeeping:** a stray `infrastructure/agent-progress.log` exists alongside `infra/` — the
      `test-runner` subagent still writes there; `infrastructure/` was superseded (see
      `.claude/rules/infrastructure.md`).
- [S] green-adapter rest (coverage: seven AI-edit DI stubs raise NotImplementedError) — no production
      change to make; the stubs the red step pins were written in `d553f2d`.
- [S] green-acceptance — **deferred to last, not skipped.** Decision (2026-07-31, user): 1.1's
      acceptance does **not** pull the message/revision read paths forward; it waits for the scenarios
      that own them (4.x revisions, 6.x messages) and runs after they land. Re-scheduled as the
      **Deferred** entry at the very end of the backend scenario sections (just above
      "## Integration Scenarios"), so that file order — the only machine-readable part of the
      next-work-unit rule — agrees with the prose. The blockage analysis that forced the decision:
      **BLOCKED, and not by anything green-acceptance is allowed to change.**
      This step may remove the disable marker and nothing else, but the marker is not what is
      holding the test. Four things the test needs do not exist:
      (1) **no AI-edit usecases at all** — `backend/usecase/src/` holds `auth`, `document`,
      `generation`, `shared`; the seven providers in `document_edit_router.py` have nothing to be
      bound to. Only the shared helper `resolve_owned_document` was built in this scenario.
      (2) **the router is not mounted** — `main.py:116-119` includes generation/auth/oauth/document
      only, and none of the seven providers appear in its `dependency_overrides` table. Both review
      passes flagged this on `d553f2d` and again on `994285e`.
      (3) **no tables** — `backend/adapters/db/migrations/versions/` has no chat-message and no
      revision migration, and nothing under `adapters/db/src/` mentions `ai_edit`, `revision` or
      `chat_message`.
      (4) the assertions need a **real happy path on two of the seven routes**: the aftermath read
      (`ai_edit_guard_statements.when_the_owner_reads_the_document_aftermath`) calls `list_messages`
      and `list_revisions` as the rightful owner and pins each to `{"items": [], "next_cursor": None}`
      with status 200 (`ai_edit_guard_assertions.py:28,85-94`). A guard that only ever refuses cannot
      satisfy that — "no rows were created" is observed through those two endpoints working.
      So the scenario's checklist has a sequencing gap: it went `red-usecase → green-usecase` for the
      guard helper alone, then straight to the adapters, and never scheduled the seven usecases the
      acceptance test drives. Closing it is a design call, not a green step — whether 1.1's acceptance
      pulls the message/revision read paths forward, or whether 1.1 waits for the scenarios that own
      them (4.x revisions, 6.x messages) and its acceptance runs last. Decide before proceeding.

### Scenario 1.2: An edit belonging to another document of the same owner is not found
- [x] red-acceptance — 3 parametrized items over the three edit-id-carrying routes
      (`EDIT_SCOPED_ENDPOINTS`: stream / state / cancel), class-level skip marker. All 3 fail in the
      **setup**, not at the assertion: `POST /api/v1/documents/{id}/ai-edits` is not mounted, so
      queueing the seed edit answers Starlette's `{"detail":"Not Found"}` instead of 202. Predicted
      exactly that (type, message and 3-failed/0-passed count all matched) — the same unmounted-router
      wall that deferred 1.1's green-acceptance, reached one step earlier here because 1.2 needs a
      *real* queued edit to exist before the cross-document probe means anything.
      Reuse over restatement: 1.1's `invoke` now delegates to a shared `invoke_with_edit`, so both
      scenarios build identical URLs, and the canonical-envelope assertion is imported from
      `ai_edit_guard_assertions` rather than copied — a second copy of the envelope could drift while
      both scenarios stayed green.
      `/test-review` fixed seven violations. The load-bearing one is the aftermath assertion: the
      red-agent had deliberately weakened the ADR's byte-identical compare to `status != "cancelled"`,
      reasoning that a live worker legitimately advances `queued → streaming → done`. The reasoning
      was sound but over-generalized — only `status` and `last_seq` actually move under the worker, and
      a negative check is satisfied by `None`, a missing key, `"CANCELLED"`, or a `/stream` refusal
      that terminalized the edit as `"error"`. It now pins positive membership in
      `STATES_REACHABLE_WITHOUT_A_CANCEL = ("queued", "streaming", "done", "error")`, the exact key
      set (so a handler leaking the *other* document's id fails), `created_at` bracketed to the queue
      call, and the spec's status-coupled invariants (`version`/`revision_number`/`changed` null
      unless `done`; `error_code` null unless `error`). Verified by driving the assertion directly
      past the skip marker: both legitimate shapes pass, all ten wrong-system shapes are rejected.
      Field coverage went 2/8, 1/7 and 1/2 → whole-response equality on all three response types.
      Two new single-purpose Statements files (`ai_edit_document_seed.py`, `ai_edit_http_status.py`)
      absorb the seeding and status literals that were duplicated across the two scenarios.
      **Carry:** 1.1's `test_document_scope_guard_acceptance.py:28,31` has the same given/when
      mislabel this review fixed in 1.2 (a `given_` method performing the docstring's When) — left
      alone as prior-commit work; fix it when 1.1 is next touched. `acceptance/conftest.py` is 234
      lines, over the 200-line limit, pre-existing. *(conftest split and the 1.1 given/when fix landed
      in the follow-up refactor commit `300c11c8`; the conftest note is resolved.)*
      **Local-only environment change, not committed:** `infra/.env` `POSTGRES_DB` was moved
      `textery → textery_s19` to get the backend to boot — the default `textery` database is migrated
      past this branch (`Can't locate revision 'b4c5d6e7f8a9'`, the same breakage line 88 recorded for
      db-layer runs, now blocking the application too). `infra/.env` is gitignored, so this does not
      travel with the commit; a fresh checkout on this host will hit the boot failure again.
- [x] design — Option A chosen, ADR at `decisions/edit-scope-guard-decision.md`. A second shared
      helper `resolve_owned_edit` over a bounded `AiEditRepository.find_scope_by_id_and_document`,
      layered on 1.1's `resolve_owned_document` and importing its `REFUSAL_MESSAGE` constant so the
      two refusals cannot drift. Rejected: a joined composite port method (ownership policy into
      adapter SQL, guard stops being the usecase's first statement) and inline-per-usecase (three
      authors, three chances to validate before resolving). Hazard scan covered all 8 `_index.md`
      groups plus one synthesis pass over 11 flagged seams; 20 GAPs, 15 owned by already-specified
      scenarios, 5 folded into the design as forced guards: (1) the AI-edit port is called **zero**
      times when the document is unresolvable (spied — otherwise the edit lookup is itself an
      unauthorized read and nothing goes red); (2) a raising/timing-out repository propagates and is
      never rendered as the canonical 404 (a later broad `except` would map a DB outage onto
      "document not found" and 1.2's own byte-identity assertion would pass); (3) `AiEditScope`
      pinned by field name `["id", "document_id"]`; (4) the step-2 refusal asserted against the
      imported literal, carrying no edit or document id; (5) step 2 emits its own log record with a
      cause discriminator distinct from step 1, carrying only the caller's own ids — client-
      indistinguishable, server-attributable. The two-read skew window was dismissed on evidence:
      the codebase has no document delete and no owner transfer, so ownership cannot change between
      the steps; the ADR names this helper as the place the cross-check goes if either ever lands.
- [x] red-usecase — 5 tests on `resolve_owned_edit`, one class, skipped at class level; all 5 fail
      (3 × `NotImplementedError` from the stub, 2 × `AssertionError` naming the outage that was
      expected to propagate). Predicted type, message and the 5-failed/0-passed count matched exactly.
      Beyond the scenario's own case (a real edit under document A is not found under document B of
      the same owner), each of the design's five forced guards is one test: the edit store is asked
      **zero** times when the document cannot be resolved; a raising store propagates unchanged
      instead of rendering the canonical 404; the projection is pinned to the literal
      `["id", "document_id"]`; the refusal is pinned to the literal `"document not found"` and carries
      no ids; the two refusals are distinguishable server-side.
      `/test-review` found both of this family's recurring weaknesses again. The distinctness check
      was `assert EDIT_SCOPE_REFUSAL_CAUSE != DOCUMENT_SCOPE_REFUSAL_CAUSE` — two constants declared
      73 lines above in the same file, so it asserted the author typed two different strings and no
      implementation could fail it; both operands are now read off the emitted records, which catches
      a guard that stamps one shared cause. The step-1 record assertion was cause + two `not in`
      substring checks with **no positive anchor**, so a record whose whole message was
      `"document-scope-refused"` passed it. More generally every log assertion was `in`/`not in`
      against an unconstrained message, so an id the guard must never record could ride along in text
      while every check for the *enumerated* ids passed: the record contract is now one id-free
      message literal compared with `==`, and all variance in structured `extra=` fields asserted as
      a **whole mapping** over `("caller_id", "document_id", "edit_id")` with a sentinel for
      must-be-absent — absence and presence now fail the same assertion. Forced guard (1) was proven
      only on the refusal path; the document-store outage test now asserts it too, paired with a
      positive control so the emptiness check cannot pass on an unwired spy. Both fakes are now bound
      to their ports — the review-pass follow-up recorded at line 96 for `FakeDocumentRepository`,
      applied here at birth rather than inherited. Verified by driving the Statements directly
      against a reference implementation plus 12 mutants — all 12 caught; under the old assertions 5
      of them passed.
      **Binding on green:** logger `document_edit.resolve_owned_edit`, INFO, exactly one record per
      refusal, causes `"document-scope-refused"` (step 1) and `"edit-scope-refused"` (step 2). Step
      1's record carries **no** ids — the document id failed to resolve; step 2's carries the path
      document id (proven the caller's) and **not** the edit id, which is the premortem's incident:
      a harvested foreign edit id passes step 1 and would otherwise land in the log. Since 1.1's
      helper emits nothing, step 1's record is emitted by `resolve_owned_edit` catching and
      re-raising — `resolve_owned_document` stays untouched.
      **Known duplication for `/refactor`:** the canonical-refusal and bounded-projection assertions
      are near-duplicates of `document_scope_guard_statements.py:105-122`, with a second
      `REFUSAL_MESSAGE` and a second `SCOPE_FIELD_NAMES` literal that can drift from 1.1's.
      **House rule bent, deliberately:** the seeded edit goes straight onto the fake — story 19 has
      no queue usecase yet (§3 lands after this guard). `FakeAiEditRepository` records that this
      collapses into a `QueueAiEdit` call once it exists.
- [x] green-usecase — `resolve_owned_edit` is two statements and one catch: `resolve_owned_document`
      first, then `find_scope_by_id_and_document(edit_id, document_id)`, `None` →
      `NotFoundException(REFUSAL_MESSAGE)` with the constant imported from 1.1's helper. The step-1
      refusal is caught **as `NotFoundException` only**, logged, and re-raised bare — never
      `except Exception`, which the RED review passes named as the incident: a broad catch that
      emits a refusal record would make a datastore outage read as a probing campaign in the one
      channel built to attribute refusals, and no test in this scenario would have caught it.
      `StorageUnavailableError` from either repository therefore passes straight through and emits
      no record. `ai_edit_scope.py` and `ai_edit_repository.py` needed no body — they arrived
      complete from the RED commit. The db adapter for this port is deliberately absent, left for
      adapters-discovery. 166 passed, 0 failed (was 161 + 5 skipped).
      One test-file change beyond the marker, flagged rather than hidden: removing the class-level
      skip left `import pytest` unused, which ruff rejects as F401; the import line was deleted, no
      assertion touched.
      `/test-coverage usecase --focus` (with `--cov-branch` added by hand — the tech template still
      omits it, see line 83): `resolve_owned_edit.py` 22/22 lines and **2/2 branches** — both sides
      of the step-1 catch and the step-2 `is None`; `ai_edit_scope.py` 6/6. One real gap:
      `ai_edit_repository.py:30`, the Protocol's `raise NotImplementedError` body, which is the
      enforcement mechanism rather than dead code (a `...` body would answer "not found" for every
      owner's own edit). Pinned by the coverage pair inserted below, following the `rest` DI-stub
      precedent at line 156.
      **Two findings carried:** (a) the same gap is open six times in 1.1's `document_repository.py`
      (13/19 lines: L27, 30, 43, 48, 54, 71) — the entire remainder to 100%, and it interacts with
      the undecided project-wide question at line 86, so it is worth pinning only once that lands;
      (b) the tech template's focus filter
      (`.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:38`) returned **zero**
      files while `git status` showed the new module modified — its pathspecs do not match this repo,
      and it fails silently into a clean report. That template has now produced two false all-clears.
- [x] red-usecase (coverage: AiEditRepository port stub raises NotImplementedError) — a **legitimate
      no-red**, following the line-156 precedent: the body this pins was written in `dde7963a`, so both
      items passed on the first run (2 passed) and **no marker was applied** — a passing coverage test
      left skipped covers nothing. Predicted "none / 2 passed", actual "none / 2 passed". The subject
      is a real empty subclass (`AdapterThatForgotToImplementThePort(AiEditRepository)`), which is the
      incident shape itself, not the Protocol. Non-vacuity proved rather than assumed: against a mutant
      port declared with a `...` body the call returns `None` and `pytest.raises` fails — the exact
      "not found for every owner's own edit" the raising body exists to prevent.
      `/test-review` found three of this family's weaknesses. (1) `pytest.raises` around an `await`
      proves nothing about awaiting — if the body ever became a plain `def`, the raise still fires with
      no coroutine created and the test stays green while the silent-coroutine hazard goes unguarded;
      `inspect.iscoroutinefunction` is now asserted first. (2) The roster came from
      `vars(AiEditRepository)`, which does not walk the MRO — a method arriving on a base Protocol (the
      natural shape once this port is split) would be invisible, the roster equality would stay true,
      and a new `...`-bodied method would slip in uncovered, which is the exact failure the pinned
      literal roster was written to prevent; discovery now unions `vars()` across `__mro__` minus the
      typing/builtins bases. (3) The bare `NotImplementedError` was asserted by type alone, so under a
      second port method it could not tell which method raised, or that the raise came from the port
      body at all — the rest DI-stub precedent already pins its message. Production now raises
      `NotImplementedError("AiEditRepository.find_scope_by_id_and_document")` and the expectation is a
      name→message dict of literals, never read back from the module.
      `ai_edit_repository.py` 6/6 lines (was 5/6, L30 missed). Usecase suite 168 passed, 0 failed,
      0 skipped.
      **Rejected, flagged not dropped:** the placement detector wanted the fake subclass, the
      invocation and the roster constants moved into an `AiEditPortStatements`. The stub family this
      test joins keeps all of it inline and has already been through review; moving one member and not
      the other buys no assertion strength. If the family moves, it moves as a pair.
- [x] green-usecase (coverage: AiEditRepository port stub raises NotImplementedError) — **not `[S]`,
      and the correction is the record.** It was first marked `[S]` on the premise "no production change
      to make", which the diff falsifies: `/test-review` demanded the bare `NotImplementedError` name
      itself, so `raise NotImplementedError("AiEditRepository.find_scope_by_id_and_document")` — a
      production change — landed inside the red commit `d065f5b3`. The message assertion never ran
      against unmodified production, so the "2 passed on the first run" claim holds for the *raise* and
      not for the *message*, and `[S]`'s "zero production files modified" condition was not met. The
      work is done and green; what was wrong was the label and the story attached to it. Carry the
      lesson rather than the excuse: a `/test-review` fix that reaches across into production turns a
      no-red into a red+green in one commit, and the skip that follows inherits a false premise.
- [x] adapters-discovery — Check 1 (ports): **db** — `AiEditRepository` has no implementation at all:
      `adapters/db/src/access/` holds only `document/document_storage.py`, `model/` has no
      `ai_edit_model.py`, `migrations/versions/` has no `ai_edits` table, and nothing under
      `adapters/db/src` mentions `ai_edit`. The guard's whole scoping guarantee currently rests on a
      `WHERE` clause that does not exist yet, which is what the premortem on `d065f5b3` called "100%
      covered and 0% proven" — the covered line is the `raise`, executed only by a test-only subclass.
      → `red-adapter db` / `green-adapter db` below.
      Check 2 (exceptions): **rest** — `[S]`, `not_found_exception_handler` already maps
      `NotFoundException` to the canonical 404 envelope, and 1.2 raises the same exception with the
      same imported literal as 1.1. Nothing new to map.
      Check 3 (response shape): **rest** — `[S]`, no new shape. 1.2's refusal is byte-identical to
      1.1's by construction, and the three edit-scoped handlers already pass `edit_id` to their
      usecase — pinned structurally, not by name order, in 1.1's `red-adapter rest` (line 108).
      **Write-here-read-there, and why this pair cannot honour it yet:** the checklist wants the
      adapter test to write through the writer usecase's port and read through the reader's. The
      writer is `QueueAiEdit`, which scenario 3.1 owns and which does not exist — the same wall that
      deferred 1.1's green-acceptance. The db test therefore seeds through the model directly, one
      layer below the port, and says so at the seam; convert it to the real write→read flow when 3.1
      lands.
      **The table this needs is deliberately two columns.** `id` and `document_id` only — the domain
      field gate applies to the schema too, and 3.1 adds `status`, `created_at`, `last_seq` and the
      terminal fields when a Statements line first reads them. An additive migration later is cheaper
      than a schema written against a spec no test has exercised.
- [x] red-adapter db — 6 tests across two classes, both skipped at class level; all 6 fail with
      `ModuleNotFoundError` — `model.document_edit.ai_edit_model` for the four query tests,
      `access.document_edit.ai_edit_storage` for the two shape guards. Predicted type, both messages
      and the 6-failed/0-passed count matched. **One prediction loop worth carrying:** the first
      prediction named the parent package `access.document_edit`, but the actual named the full dotted
      path — `adapters/db/tests` is on `pythonpath`, so the new *test* directory merges into the same
      implicit namespace package as the production `access/` tree. Harmless today (already true of
      `access/document` and `access/auth`), but a test-side module can shadow a production one by name.
      `/test-review` found three strictness holes, each an instance of a weakness this family keeps
      producing. (1) `sql_recorder.selected_columns()` stripped the table qualifier, so
      `SELECT documents.id, documents.document_id FROM documents JOIN ai_edits …` — the two column
      names read off the **wrong table** — satisfied an assertion whose entire claim is that the finder
      read only its own columns; a new `qualified_selected_columns()` pins the literal
      `["ai_edits.document_id", "ai_edits.id"]`, and `selected_columns()` delegates so 1.1's suite is
      untouched. (2) The recorder guard was `assert self._recorded_sql.statements` — truthiness where
      the count is deterministic, so a finder emitting a full-entity read **plus** a projection passed
      it; now `len(...) == 1`, covering the zero case (listener never fired, which reads as a clean
      pass) and the >1 case in one message. (3) The keyword-only check inspected `edit_id`/`document_id`
      by name and ignored the rest of the signature — the 1.1 `dataclasses.fields()` lesson applied to
      a signature, since an adapter growing a third positional same-typed UUID passed the very guard
      built to stop transposition; the whole signature is now a hand-written positional literal.
      Structural: `find_scope_watching_what_it_reads` returns a `WatchedScopeRead(scope, recorded)`
      instead of stashing the recording on the instance, which had made the projection assertion
      silently dependent on a different method having run first — and the likeliest way to trip it
      reported "no SQL captured", misdiagnosing wiring as an adapter defect. The two static shape
      guards moved to their own session-free `ai_edit_port_shape_statements.py`.
      db suite 56 passed, 6 skipped; 1.1's document-scope projection test, the consumer of the
      refactored recorder, still passes.
      **Binding on green:** the qualified literal pins the table name `ai_edits`, which the ADR states
      and no migration yet establishes — a differently-named table fails on the name, which is correct
      but is now a pinned decision rather than an incidental one. `TRUNCATE_ALL` needs no change: the
      FK to `documents` means `TRUNCATE … CASCADE` reaches it.
      **Two seams recorded in code, not hidden:** `given_a_queued_edit` seeds through the model, one
      layer below the port (`QueueAiEdit` is 3.1's — convert to the real write→read flow then); and
      production symbols are resolved lazily inside helpers so the six failures land in the call phase
      rather than as fixture setup errors. Both carry a "collapse at GREEN" note.
      **Left for `/refactor`:** duplication with `document_storage_statements`.
- [x] green-adapter db — migration `2b3c4d5e6f7a` (new head, down_revision `1a2b3c4d5e6f`), the model,
      and `SqlAlchemyAiEditStorage.find_scope_by_id_and_document` as
      `select(AiEditModel.id, AiEditModel.document_id)` with both ids in the WHERE — a column
      projection, so the recorder's qualified literal holds at the SQL rather than at the DTO. Keyword-
      only, and **structural** conformance (no Protocol inheritance), as `SqlAlchemyDocumentStorage`
      does. `migrations/env.py` gained the model import — without it `Base.metadata` lacks the table and
      autogenerate would propose dropping it. 6/6 target tests, full db suite 62 passed, 0 failed.
      `alembic upgrade head` clean; `downgrade -1` then `upgrade head` both succeed.
      **Both review-pass obligations shipped, verified against the live table** (`\d ai_edits`):
      `ai_edits_pkey PRIMARY KEY (id)` and `ai_edits_document_id_fkey FOREIGN KEY (document_id)
      REFERENCES documents(id) ON DELETE CASCADE`. **Neither is pinned by a test** — a later migration
      could drop either and the suite stays green. `TRUNCATE_ALL` needed no entry, and this was
      confirmed empirically rather than by reading: `count(*) from ai_edits` is 0 both before and after
      a full 62-test run that seeds edits in 4 of them.
      `/test-coverage db --focus` (with `--cov-branch` by hand): `ai_edit_storage.py` 12/12 lines,
      `ai_edit_model.py` 9/9. **One number that proves less than it looks:** the finder's guard is a
      ternary (`... if row else None`), and coverage.py instruments `if`/`while` statements, not
      conditional expressions — so "0/0 branches" means *nothing was measured*, not *both arms ran*.
      The `None` arm was checked by hand and is exercised by the two cross-document cases, which is the
      authorization arm. On this stack, guard logic written as a ternary is invisible to `--cov-branch`
      even when the flag is present.
      **Tech-template defect, now root-caused:** the focus filter
      (`.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:38`) returned zero files
      again, because `git diff HEAD --name-only` never lists **untracked** paths — so any green phase
      that creates new files instead of editing existing ones always yields an empty filter, and an
      empty filter reports clean. Fix is `git status --porcelain`, or union with
      `git ls-files --others --exclude-standard`. Third false all-clear from that template.
      **Left for `/refactor`:** the lazy production imports in both Statements files can collapse to
      module scope now that the modules exist.
- [S] green-acceptance — **deferred to last, not skipped**, mirroring 1.1's disposition and by the same
      2026-07-31 decision, which this step applies rather than re-opens: an acceptance test does not pull
      the paths it depends on forward, it waits for the scenarios that own them. Re-scheduled as the
      **Deferred: Scenario 1.2** entry at the very end of the backend scenario sections, so file order —
      the only machine-readable part of the next-work-unit rule — agrees with the prose.
      The blockage was re-verified against the tree at this step, not inherited from the discovery note:
      `main.py:116-119` mounts generation/auth/oauth/document and **not** `document_edit_router`;
      `usecase/src/document_edit/` holds the guard helper, the port and the scope and **none** of the
      seven usecases; no file under `application/src` mentions `document_edit`, so nothing is wired even
      if it were mounted. This step may remove the disable marker and nothing else, and the marker is
      not what holds the test.
      1.2 needs strictly more than 1.1. Its setup queues a **real** edit through `POST /ai-edits` —
      deliberately, because a fabricated id is refused by any handler that merely fails to find it and
      the path document id would never be consulted, which is the whole scenario — so it waits on
      **3.1** for `QueueAiEdit`. Its aftermath read is a whole-body `GET /ai-edits/{edit_id}` under the
      edit's own document, which waits on the state endpoint in **4.x**.
      Everything 1.2 itself owns is done and green: the design and its ADR, the guard with all five
      forced guards, the port, the `ai_edits` schema and the scoped finder.

### Scenario 1.3: A revision belonging to another document of the same owner is not found
- [x] red-acceptance — 1 test on the single revision-carrying route (`POST /revisions/{n}/restore`),
      class-level skip marker. It fails in the **setup**, one wall earlier than 1.2's: a revision is
      only recorded when an AI edit applies (§7.2), so the seed must queue a real edit first, and
      `POST /ai-edits` is not mounted — Starlette's `{"detail":"Not Found"}` instead of 202. Predicted
      type, message and the 1-failed/0-passed count matched exactly.
      Reuse over restatement: the canonical-envelope assertion is imported from 1.1's
      `ai_edit_guard_assertions.assert_is_the_canonical_refusal` (as 1.2 does), and 1.2's private
      queue-seed was **extracted** to a shared `ai_edit_queue_seed.py` rather than copied — both
      scenarios now queue through one strictly-asserted seed. New `ai_edit_revision_seed.py` drives
      that edit to a terminal state on a bounded 20s poll, requires `done`, and cross-checks the
      reported `revision_number` against the document's own `GET /revisions` page: taken from the edit
      alone, a backend reporting a revision it never wrote would seed a scenario whose subject is
      false and the refusal would be correct for the wrong reason.
      "No new version is created on either document" is asserted, not implied: **both** documents are
      read whole-body plus whole revision page before and after the probe and compared. Both, because
      a handler that resolved the revision number and applied it to its *own* (first) document would
      leave the path document untouched and pass a second-document check alone. The revision page is
      pinned alongside the body because a restore writes its revision row in the same transaction as
      the new version — an added row is the tell that it ran and then lost the version CAS.
      `/test-review` found a **spec violation, not merely a loose assertion**, and it was live:
      `documents_revisions_list.yaml` says the first mutation of a never-edited document writes **two**
      revisions in one transaction — revision 1 carrying the pre-mutation content with source `manual`,
      then revision 2 carrying the result. The seed asserted `revision_number >= 1`, which accepts
      **revision 1**, i.e. a backend that wrote only the baseline and never applied the edit. The
      scenario's whole subject ("a revision recorded on the first document") could have been false
      while the cross-document 404 passed for the wrong reason. Now `== 2`, with `version == 2` and
      `changed is True` — `changed: false` means no revision is recorded at all, so it is the premise
      and is asserted rather than assumed.
      Three more of this family's weaknesses were live. The entire "no new version" proof was
      **relative only** (`after == before`), which a seed that recorded nothing satisfies perfectly;
      both documents are now pinned to absolute spec-derived state as well — the second at version 1
      with `EMPTY_PAGE`, the first at version 2 with the exact two-row page
      `[(2,2,"ai"), (1,1,"manual")]`, newest first, `next_cursor` null, closed field sets. The relative
      and absolute checks fail differently on purpose and both are kept. The premise "the second
      document deliberately has no revisions" lived in a docstring and was **never asserted** — if a
      revision leaked onto it the probed number would legitimately exist there and the 404 would be
      testing something else. And the two baseline reads had no status guard, so an unvalidated error
      body as `before` compared equal to an equal error body as `after`; all four reads are pinned to
      200 through one helper.
      Two values are deliberately not exact (determinism hierarchy cat. 4): the applied `content` is
      model output, but it is **not** a presence check — the pre-edit value is known exactly (`""`) and
      `changed: true` was required, so it is asserted to differ from that known value; `last_seq`
      counts model-produced stream events and is bounded below by the terminal event.
      **Carried mislabel fixed in both scenarios:** `then_both_documents_are_read_back` was an action
      wearing a `then_` name, asserting nothing and threading its result back through the test class.
      1.2 carried the identical defect (`then_the_edit_is_read_back_under_its_own_document`) and was
      fixed with it, since it is the same defect class and the file was already open. 1.1 was left
      alone — its 7 items were only required to keep collecting, and they do; bringing its naming in
      line is a separate mechanical pass.
      11 items collect (1.1: 7, 1.2: 3, 1.3: 1), 11 skipped, every marker intact. RED re-verified by
      lifting each marker and restoring it: 1.3 still fails at `ai_edit_queue_seed.py:63`, and 1.2's
      three items still fail at that same shared seed assertion — the extraction did not weaken it.
      **Environment:** the backend had to be started for this run
      (`docker compose -f infra/docker-compose.yml up -d --build backend`); `/health` answers 404 on
      this build, so liveness was confirmed by the app answering on an API path instead.
- [x] design — Option A chosen, ADR at `decisions/revision-scope-guard-decision.md`. A third shared
      helper `resolve_owned_revision` over a bounded
      `DocumentRevisionRepository.find_scope_by_number_and_document`, layered on 1.1's
      `resolve_owned_document` and importing its `REFUSAL_MESSAGE` — the same shape 1.2 froze for
      edits. Rejected: one parametric child-scope resolver shared by edit and revision (the child key
      types differ, UUID vs int, as do the log causes and the scopes — the parameterisation is wider
      than the duplication it removes), a composite port join, and an inline lookup in the restore
      usecase. Hazard scan covered all 8 `_index.md` groups plus one synthesis pass over the flagged
      seams; 14 GAPs, 8 folded into the design as forced guards, the rest dismissed on evidence.
      **The fold worth carrying is the range check.** `revision_number` is a plain Python `int` and
      Python ints are unbounded; the column is not. Passing the raw value to the repository sends a
      value above the int4 bound to the driver as a numeric-out-of-range error, and the design's
      deliberately narrow `except NotFoundException` correctly does *not* swallow it — so it surfaces
      as a 500, which `documents_revisions_restore.yaml` explicitly forbids ("overflowing → 404").
      The helper therefore pins `1 .. 2147483647` and refuses outside it **with the repository asked
      zero times**; §1.4 keeps only the rest-layer non-integer edge, where FastAPI's `int` path typing
      would answer 422.
      The other seven folds: the db test seeds **three** revisions so number 3 resolves the third row
      and 4 is 404 (the numbering base was asserted only by the parameter name, which a 0-based store
      satisfies); **both** repositories driven to raise propagate unchanged and emit no refusal record
      (1.2 proved this for step 1 only); the two refusals asserted equal in type and message, not
      merely each equal to the imported literal; a rest-layer guard that POSTs a body carrying
      `document_id`/`owner_id`/`version` and asserts the usecase is awaited with the **path** ids (the
      restore contract ignores any body, and a Pydantic body model added later turns the 404 into a
      422); the scope field names pinned to the literal `["revision_number", "document_id"]` with the
      finder recorded as a column projection; four log tests — step-1 cause id-free, step-2 cause
      carrying `document_id` and **never** the probed revision number, success emitting neither,
      outage emitting neither; and the FK `ON DELETE CASCADE` **pinned by a test**, which 1.2 shipped
      unpinned and its own review pass flagged.
      **Three dismissals made on evidence rather than assumption**, because groups 02, 03 and 04 each
      independently raised the first one: there is no TOCTOU window between step 1 and step 2 — no
      document delete route exists under `router/document/` and no owner-transfer usecase exists under
      `usecase/src/document/`, the same evidence 1.2's ADR used; no document non-live state —
      `document.py` mints only `DRAFT_STATUS`, so the archived/soft-deleted case cannot arise and
      re-fires the day a lifecycle state lands; and no N-1 schema risk — the migration is purely
      additive, a new table holding the child side of the FK, so no already-deployed document path can
      break on it. Group 08 (client/frontend) was block-dismissed as out of altitude.
      **Both review passes returned CONCERNS and four findings were folded back into the ADR before
      red-usecase could lock on it** — the passes are non-gating, but these landed in the design
      artifact itself, which is still what this work unit ships. (a) Both passes independently found
      the missing `UNIQUE(document_id, revision_number)`: the `| None` return is `one_or_none()`-shaped,
      restore writes a revision row per call, and two concurrent restores each computing `max(n) + 1`
      produce the same number — `MultipleResultsFound` is then a 500 on the guard path, the same
      failure class the range check exists to prevent arriving by a different door. `ai_edits`' PK is
      its own UUID and inherits nothing here. (b) Both found the non-integer edge was deferred to §1.4
      *under a 422 expectation*, but the contract lists no 422 at all and puts "non-integer" in the 404
      body; `document_edit_router.py`'s own docstring already rejects a pre-guard 422, and path
      coercion fires ahead of the Bearer dependency, so an unauthenticated caller would get 422 instead
      of 401. The route now declares the parameter as `str` and the guard parses it, which also merges
      the parse and the range check into one place. (c) The premortem's leak: `RevisionScope` carried no
      row `id`, and `revision_number` is per-document, so the natural §7.x content loader keyed on the
      number alone would copy another document's revision text into the caller's document — a
      cross-tenant leak that is also a write. The scope carries `id` and the content port is `id`-keyed.
      (d) "Step-1 cause id-free" was written literally but mirrors a helper that always emits
      `caller_id` and omits only the peer id; taken at face value it would make step-1 refusals
      anonymous in the one channel built to attribute them. `_log_refusal` is shared with
      `resolve_owned_edit`, not copied.
      Two findings were **not** folded and are carried instead: the review pass's note that the
      dismissals decay silently (nothing goes red the day a delete route or a lifecycle state lands —
      the ADR's "re-decide here" is prose only), and its observation that this file left no `[~]`
      marker after the step advanced, fixed here.
- [x] red-usecase — 12 tests on `resolve_owned_revision`, one class, skipped at class level; all 12
      fail — 10 × `NotImplementedError` out of the stub and 2 × `AssertionError` as predicted, then
      **8 / 4** after `/test-review` (see below); the 12-failed/0-passed total and the three messages
      never moved. Predicted type, both messages and the count matched exactly. Beyond the scenario's own case, each of the design's eight forced guards is at least
      one test: the revision store is asked **zero** times when the document cannot be resolved;
      out-of-range numbers (`0`, `-1`, `-2147483648`, `2147483648`) are the canonical refusal with
      the store never asked, and `1`/`2147483647` are carried through *as parsed ints* so an
      off-by-one bound goes red somewhere; non-integer input is the canonical refusal, never a 422;
      `RevisionScope` is pinned to the literal `["id", "revision_number", "document_id"]`; either
      repository raising propagates unchanged; and four log tests cover the two causes, the success
      path and both outages. (The step-1/step-2 cross-comparison this list originally claimed was
      **removed** by `/test-review` as an unfailable tautology — see below. Both refusals are still
      pinned, each against the literal imported from 1.1.)
      **Two judgement calls worth carrying.** (a) The non-integer set is deliberately
      `("abc", "1.5", "", "2e3", "0x2", "-")` and deliberately excludes `" 2"`, `"+2"`, `"1_0"` and
      the Arabic-Indic `"٢"` — `int()` accepts all four, so demanding a refusal for them would pin a
      parser opinion this scenario has not formed. What is in the set are the numeric-looking
      strings a `float()` or a lenient regex would let past into the store. (b) The ADR's
      "`_log_refusal` is shared with `resolve_owned_edit`, not copied" cannot be honoured by literally
      sharing the message: 1.2 pins `"ai edit guard refused the request"` on logger
      `document_edit.resolve_owned_edit`, and a shared line or a shared logger would break that test
      in GREEN, where tests are read-only. What is genuinely shareable is the `extra`-building rule,
      so it is asserted **between** the guards: `refusal_record_shape_statements` drives both
      resolvers and compares their id-field key sets, both sides read off emitted records rather
      than off a literal. **Binding on green:** `_log_refusal` takes the logger and the message as
      parameters; the revision guard's own literals are logger `document_edit.resolve_owned_revision`,
      message `"revision guard refused the request"`, causes `"document-scope-refused"` and
      `"revision-scope-refused"`.
      Reuse over restatement: `document_guard_contract` (actor ids, `captured`,
      `assert_is_the_canonical_refusal`, `assert_bounded_projection`), `FakeDocumentRepository`,
      `FailingDocumentScopeRepository` and `StorageUnavailableError` are all imported, not recreated;
      1.2's private `_RecordingHandler` plus its attach/force-INFO/restore-level bookkeeping was
      **extracted** to `statements/log_recorder.py` and 1.2 now imports it — three copies of "remember
      to put the level back" is three chances to leave a process-global `setLevel` behind. 1.2's five
      tests re-verified green after the extraction.
      **Two pre-existing reds inherited, not introduced** (both confirmed present at HEAD by stashing):
      `ruff` flags `SIM300` in `test_ai_edit_repository_port_stub.py:69`, and `mypy` fails on
      `document_guard_contract.py:84` (`fields()` takes a dataclass, not `object`) — the CI mypy step
      added at 1.1's green-adapter is therefore red on this branch already, and per the line-104 note
      its trigger does not fire on feature branches, so nothing was reporting it.
      `/test-review` found seven strictness holes and made one removal; the failure breakdown moved
      from 10 × `NotImplementedError` / 2 × `AssertionError` to **8 / 4** as a result, with the same
      12-failed total and the same three messages, so the skip-reason text stayed accurate.
      Two are this family's signature weaknesses arriving again. The cross-guard roster was
      **self-fulfilling**: `ALL_ID_FIELDS` was unioned from the two guards' own test-side tuples, so a
      guard growing a field in neither tuple filtered out of both sides and the class stayed green on
      exactly the drift it advertises. It now reads the record's real extras (`record.__dict__` minus
      standard attributes sampled from `logging` itself) and compares the whole set, with
      `refusal_cause` *expected* rather than excluded — an exclusion list is the same hand-maintained
      roster in negative form. And the byte-identity check between the two refusals was an **unfailable
      tautology**: `(type, str)` compared between two operands pinned two lines above by the same
      `assert_is_the_canonical_refusal` helper. Removed — no implementation reaching it could fail it,
      and its docstring's defence ("a change touching only one raise site") is already covered by both
      sides going through that one shared function.
      One hole was more than looseness. The record accessors used `_first` truthiness, and the
      cross-guard shape test reaches them without ever calling
      `assert_each_refusal_emitted_exactly_one_record` — so a guard emitting a **duplicate** pair, a
      probe double-counted in the one channel built to attribute probes, passed with only `records[0]`
      inspected. Exact cardinality now, in 1.2's twin file too. The success-path test was named "when
      the revision resolves" but asserted only silence, which a guard returning `None` or another
      document's row also produces — it carries a full `RevisionScope` equality as its positive control
      now, mirroring the class's existing `assert_each_outage_reached_the_caller`. An assertion was
      hidden inside an act step (`request_the_revision_under_the_foreign_document` called `refusal_of`,
      enforcing a contract no line of the test body showed). Four roster loops iterated the recorded
      dict instead of the pinned tuple, so a probe never sent could not fail on its own value. And the
      scenario's second Then — "no new version is created on either document", claimed by both the
      docstring and the ADR — was **asserted nowhere**: a guard that refused correctly and bumped a
      version satisfied every other assertion in the package. It is now pinned to the `Document.create`
      literal rather than sampled from the row.
      Usecase suite 168 passed, 12 skipped, 0 failed; ruff clean across `backend/usecase/tests`. RED
      re-verified by lifting the marker (12 failed, 0 passed) and restoring it.
      **Left for `/refactor`, flagged not dropped:** `RevisionRefusalLogStatements` is a near-total copy
      of 1.2's log Statements (`_assert_shape`, `_assert_ids`, `_collected`, both accessors, and the
      same sentinel declared twice under two names), and `assert_outage_propagated` / `_outcome_of` /
      `assert_*_lookups` each exist in two or three copies — the prescribed fix is a
      `RefusalLogStatementsBase` plus promoting the outage helpers into `document_guard_contract.py`.
      **`conftest.py` is at 180 lines** and grows one fixture per scenario; it crosses the 200-line hard
      limit within a few more.
      *(Done at `/refactor`, below — all three, plus both inherited mypy reds.)*
- [x] refactor — the three deferred findings, applied serially with the suite re-run after each.
      (1) `RefusalLogStatementsBase` extracted, mixed into both log Statements classes ahead of their
      guard bases so the guard's `refusal_of`/`second_document_id` win the MRO; what differs between
      §1.2 and §1.3 is now four class attributes (`logger_name`, `refusal_message`, `child_id_field`,
      `child_scope_refusal_cause`) and nothing else. The base landed at 215 lines, over the hard limit,
      so it split again on a real seam: `refusal_log_base.py` gets hold of a record (recorder lifecycle,
      act steps, accessors, cardinality) and `refusal_record_assertions.py` judges one (shape, id
      mapping, cause distinctness). The `"<absent>"` sentinel is declared **once** there — it had been
      two constants under two names, in the one family whose whole subject is that the two guards mean
      the same thing by "absent". `_assert_ids` builds `actual` from the pinned `id_fields` roster, not
      from the expectation's own keys: derived from `expected`, a dropped field drops from both sides.
      (2) Outage helpers promoted into `document_guard_contract.py` — `captured_outage`, `outcome_of`,
      `assert_is_the_store_outage`, `assert_lookups`. Three copies of the propagation equality and two
      of the capture-without-judging act helper collapse to one each; the two `assert_*_lookups`
      wrappers stay on their guard bases (protected, intent-named) but share the comparison.
      (3) The root `usecase/tests/conftest.py` is gone, replaced by four per-directory conftests
      (`auth/` 99, `document_edit/` 73, `generation/` 22, `document/` 10). Beyond the line count, this
      ends the arrangement where every test in the module imported every Statements class in it.
      **Both inherited mypy reds fixed, since both sat in files this pass was already rewriting:**
      `assert_bounded_projection` takes `DataclassInstance` under `TYPE_CHECKING` rather than `object`,
      and `assert_is_the_canonical_refusal` takes `object` rather than `Exception` — the boundary probe
      hands it whatever the guard produced, and "returned a scope where it should have refused" is one
      of the outcomes that equality exists to catch, so the narrow type had presumed the case away.
      `python -m mypy` is now **clean across all 306 files** (HEAD had two errors, not the one the entry
      above recorded). The ruff `SIM300` is untouched and is **not** at
      `test_ai_edit_repository_port_stub.py:69` as recorded above — it is at
      `adapters/rest/tests/router/document_edit/test_ai_edit_router_di_stubs.py:50`, outside this pass.
      Usecase suite 168 passed / 12 skipped / 0 failed, unchanged; ruff clean across `usecase`; RED
      re-verified twice by lifting the marker (12 failed, 0 passed) and restoring it. Every touched file
      is under 200 lines. Full backend suite 563 passed, 4 failed — all four the known unmigrated-db
      environment failure (`relation "ai_edits" does not exist`), no db code touched.
      **Carried:** `generation_lifecycle_statements.py` is 227 lines, over the hard limit, pre-existing
      and untouched by this pass.
      **Review passes over the behavior commit `009a464f`: agent-review CONCERNS (4), premortem
      CONCERNS (2 credible).** Two findings were stale claims in this file itself and are corrected in
      the `red-usecase` entry above. Three more are scheduled as work rather than carried as prose —
      the two inserted steps below and the `adapters-discovery` annotation.
      **The premortem's first incident is the one to read before green**, because it is a hole in the
      test package rather than in the design: the pre-store range/parse check has **no refusal cause**,
      and nothing pins its position relative to step 1. Three different GREENs satisfy all twelve
      tests — emit nothing, emit `revision-scope-refused`, or emit a third cause the shape test never
      sees. Put the check first, which is the natural reading of "before the repository is called" and
      what the module docstring already says, and `POST /documents/{victim-id}/revisions/0/restore`
      returns the canonical 404 having called neither repository and logged nothing: the step-1
      attribution record becomes suppressible by choosing an out-of-range number. The twelve stay green
      because `RevisionNumberRangeStatements` probes only the caller's own resolvable document and
      attaches no recorder at all, while the log and silence Statements probe only the in-range `"2"`.
      **Correction to how this was first scheduled:** it said "close it at green-usecase with two
      tests", which GREEN may not do — tests are read-only there. It is its own red/green pair, inserted
      below. Until that pair lands, whatever ordering green-usecase picks is unpinned, and the pair is
      what makes it binding rather than incidental.
      Two findings stay as notes. `RevisionNumberRangeStatements` shares one `_refusals` dict across its
      two probe rosters; today each test calls one act step so it holds, but a test calling both on one
      instance — which the class docstring invites — fails the roster equality for a reason unrelated to
      the guard, blaming a probe that was in fact sent. And `FakeDocumentRevisionRepository`'s docstring
      claims subclassing the Protocol protects against a port rename; it does not — a `Protocol`
      subclass without `@abstractmethod` enforces nothing at class-creation time. The rename *is*
      caught, but by the inherited raising body, so the two docstrings disagree about which mechanism
      protects what.
- [x] green-usecase — `resolve_owned_revision` is `resolve_owned_document` → parse and range-check →
      revision lookup. 12/12 target tests, full usecase suite 180 passed, 0 failed; ruff and mypy clean.
      **The ordering is the whole content of this step, and no test would have caught the wrong one.**
      The cheap check first is observationally identical to the caller — both answer the same canonical
      `NotFoundException` — but it lets `/documents/{someone-elses-id}/revisions/0/restore` return that
      404 having called **neither** repository and emitted **no** record, turning "pick an out-of-range
      revision number" into a switch that disables the step-1 attribution channel while document-id
      probing continues at full speed. green-agent verified rather than assumed that the suite cannot
      tell the two apart: the range Statements arrange only documents the caller *does* own, so step 1
      succeeds on every one of their probes and both orderings leave the same empty revision-store call
      log; the log Statements never probe an out-of-range number under an unresolvable document. The
      reasoning is written into the guard's docstring so the next reader does not "optimize" the cheap
      check forward, and the inserted red/green pair below is what makes it binding rather than
      incidental.
      Both step-2 doors — unparseable/out-of-range, and simply absent — refuse through one
      `_refuse_at_step_two`, so neither the body nor the record tells the caller which one answered.
      Range bounds are the two literals `1` / `2147483647`, not `2**31 - 1`.
      The ADR's "shared, not copied" is now honoured as far as it can be: a new
      `document_edit/refusal_log.py` holds `log_refusal(logger, message, cause, owner_id, document_id=None)`
      and `DOCUMENT_SCOPE_REFUSAL_CAUSE`, and **`resolve_owned_edit` was rewired onto it** — its private
      `_log_refusal` and its own copy of the cause constant are gone, behavior unchanged and 1.2's tests
      confirm it. Logger and message stay parameters because 1.2 and 1.3 each pin their own literals in
      read-only tests.
      One test-file change beyond the marker, flagged rather than hidden: removing the class-level skip
      left `import pytest` unused (ruff F401); the import line was deleted, no assertion touched.
      `/test-coverage usecase --focus` (run by hand as `pytest --cov=usecase/src --cov-branch`, since
      the template still omits the flag): `resolve_owned_revision.py` 37/37 lines and **6/6 branches**,
      `refusal_log.py` 8/8 and 2/2, `resolve_owned_edit.py` 22/22 and 2/2, `revision_scope.py` 7/7.
      The ternary quirk did not bite and was checked rather than trusted — no conditional expressions
      exist in any of the five files and `BrPart` is 0 throughout, so the 6/6 is measured. One thing
      `--cov-branch` genuinely cannot see was verified by hand: `not SMALLEST <= parsed <= LARGEST` is a
      chained comparison counted as a single branch pair, so the two out-of-range doors are not
      distinguished by the tool — `revision_number_range_statements.py:16` probes
      `("0", "-1", "-2147483648", "2147483648")` and pins both inclusive bounds, so both arms are held
      by named tests.
      **The focus filter's blind spot is wider than the carryover records**, and this is the fourth
      false all-clear from that template. `git diff HEAD --name-only` misses untracked files —
      `refusal_log.py` — *and* every file the RED commit already landed, which is where the ports always
      live on this project's cycle: `document_revision_repository.py` is neither modified nor untracked,
      and it holds the single real gap (line 35, the `raise NotImplementedError` body, uncovered because
      every usecase test runs against the fake that overrides it). Pinned by the pair below; no new step
      needed.
      **`/refactor` was empty and the commit skipped** — a reasoned rejection, not an omission. The
      step-1 block is now four identical lines in both guards, but extracting it needs five parameters
      to remove four lines, puts a `raise`-through behind a call so "step 1 can end the function" stops
      being visible at the call site, and is precisely what row 1 of the ADR's rejected table refused: a
      parametric resolver shared by edit and revision. The ADR drew the line at the *logging rule*,
      which is already extracted. Past the silhouette the step-2 shapes are not near-identical anyway —
      the revision guard has two doors into the refusal and routes both through `_refuse_at_step_two`,
      the edit guard has one and inlines it, and the key types, cause literals and return types all
      differ.
      **Review passes: agent-review CONCERNS (3), premortem CONCERNS (3 credible).** One was a one-line
      production defect and is fixed in this work unit rather than carried: `log_refusal` emitted
      without `stacklevel=2`, so folding the two per-guard `_log_refusal` bodies into one function moved
      **all four refusal sites in both guards** onto `refusal_log.py` as their `filename`/`lineno`/
      `funcName`. No test reads those attributes — the cross-guard shape check subtracts every standard
      `LogRecord` field before comparing — which is exactly why the regression was silent. The rest are
      scheduled below or annotated onto the gate that owns them.
      **The premortem's first incident deserves reading in full before this scenario closes, because it
      says the argument this whole work unit is about has no receiver.** `refusal_log` emits at INFO,
      and the deployed app configures logging **nowhere**: `application/src/app/main.py` does
      `import logging` and `getLogger(__name__)` and nothing else — no `basicConfig`, no `dictConfig`,
      and the same across `adapters/rest/src`. An unconfigured root leaves `document_edit.*` at WARNING
      with no handler, so every refusal record ever emitted by 1.2's shipped guard and by this one is
      dropped in production. Even at INFO the stdlib default formatter renders `%(message)s` only, and
      the message is deliberately id-free, so `refusal_cause`/`caller_id`/`document_id` would still not
      appear without a structured formatter. The 180 tests cannot see it: `log_recorder.RecordingLogger`
      calls `setLevel(logging.INFO)` and attaches its own handler, then reads the `LogRecord` object
      rather than formatted output — it forces the exact condition production lacks. This is an
      application-layer gap, not a usecase one, so it is recorded here and belongs to an infrastructure
      or application scenario rather than to 1.3's remaining steps.
- [x] red-usecase (coverage: DocumentRevisionRepository port stub raises NotImplementedError) —
      **scheduled by the review passes, following the 1.2 precedent at line 331.** The port's own
      docstring calls the raising body load-bearing — "a `...` body on an `async def` is a concrete
      coroutine returning `None`, so an adapter that forgot to implement the method would silently
      answer 'not found' for every owner's own revision" — and nothing in the commit can go red on it:
      every usecase test runs against the fake, which overrides the method, so the production body is
      never executed. 1.2 built exactly this guard, and this work unit edited that very file without
      adding the sibling. Mirror it — roster equality unioned across the MRO, plus the raising body and
      its message asserted as literals, never read back from the module.
      **Confirmed by measurement, not only predicted.** `/test-coverage usecase --focus` over the
      green phase (run by hand with `--cov-branch`, which the tech template omits) reports
      `document_revision_repository.py` at 5/6 statements — `L35`, the `raise NotImplementedError`,
      is the single uncovered line in the whole focus set. Every other touched file is 100% line and
      100% branch. So this pair is the only coverage work 1.3's usecase layer owes, and no further
      red/green steps were inserted.
      **The focus filter would not have found it.** `git diff HEAD` lists neither `refusal_log.py`
      (untracked) nor `document_revision_repository.py` (committed in RED) — and the gap is in the
      latter. The filter's blind spot is therefore wider than the carryover records: not just new
      files, but every file the RED commit already landed. Pass the names explicitly.
      **Outcome: a legitimate no-red, and this time the `[S]` condition genuinely holds.** Predicted
      "none / 2 passed", actual "none / 2 passed"; no disable marker applied, since a passing coverage
      test left skipped covers nothing. Unlike 1.2 (line 358), **zero production files were modified** —
      `document_revision_repository.py:35` already raised
      `NotImplementedError("DocumentRevisionRepository.find_scope_by_number_and_document")` with the
      exact message the test pins as a literal, so both the raise *and* the message ran against
      unmodified production. Non-vacuity was proved by measurement, not assumed: with the body swapped
      to `...` the await returns `None` and the body test fails `DID NOT RAISE NotImplementedError`,
      while the roster test correctly stays green — so the failure is attributable to the body
      assertion alone. `/test-review` found **nothing** across all four clusters: the file inherits all
      three hardenings 1.2 earned (`inspect.iscoroutinefunction` asserted before the `pytest.raises`
      block, roster unioned across the MRO rather than `vars()`, message equality against a literal),
      and the 009a464f trap is absent — the expected side is a hand-written literal dict, the
      discovered side derives from `__mro__` alone, and the two are compared with symmetric equality so
      both an added and a removed port method fail. Usecase suite 182 passed, 0 failed, 0 skipped.
      **`/refactor` empty and the commit skipped — a reasoned rejection.** The two stub files are
      near-twins, but the residue must stay per-file anyway (each port's own import, its own literal
      `EXPECTED_PORT_METHODS`, and its own kwargs — `revision_number=1, document_id=…` vs
      `edit_id=…, document_id=…`), threading the last through a helper means a kwargs dict, which is
      the "parameterisation wider than the duplication it removes" the ADR rejects and which destroys
      the fail-loudly property a differing second port method needs. Net lines go up. The Statements
      move rejected for 1.2 at line 354 was re-derived as a shared *module* and rejected on the same
      merits; a pair-wide proposal is admissible, this one is still wrong.
      **Two low-severity review findings, flagged not dropped — both apply to the 1.2 sibling equally,
      so they move as a pair or not at all.** (a) The roster comprehension collects any public class
      attribute, not only coroutine methods, so a public constant or nested alias added to a port would
      fail the roster test with a message that misattributes it as a method; filtering discovery on
      `iscoroutinefunction` would also document that the roster is the awaited-port surface. Fails
      loudly, only for the wrong reason. (b) `iscoroutinefunction` protects against the *body* becoming
      a plain `def`, not against `asyncio_mode = "auto"` (`backend/pyproject.toml:20`) being flipped to
      `strict` or the plugin being dropped — then the body test is an un-awaited coroutine that never
      executes and can report green, making the file's whole claim false while passing. An explicit
      `@pytest.mark.asyncio` is inert under auto mode and load-bearing if the mode ever changes.
- [S] green-usecase (coverage: DocumentRevisionRepository port stub raises NotImplementedError) —
      **`[S]` verified against the diff, not against the prediction, precisely because 1.2 got this
      wrong at line 358.** `git show --name-status 56878c76` lists exactly two paths: the new test file
      and `progress-backend.md`. No file under `backend/usecase/src/` appears, so `[S]`'s condition —
      zero production files modified — is met here in a way it was not for 1.2, where `/test-review`
      had forced the `NotImplementedError` message string into the red commit.
      Coverage confirms the step bought what it was scheduled for:
      `usecase\src\document_edit\document_revision_repository.py` now reports **6/6 statements, 0/0
      branch, 100%** (was 5/6, L35 missed). Run by hand as
      `--cov=document_edit.document_revision_repository` — note that a *path*-form `--cov` argument
      (`--cov=usecase/src/.../document_revision_repository.py`) fails silently into
      `No data was collected` plus a clean-looking `182 passed`, which is the same false-all-clear shape
      the carryover already records for the focus filter. Use the dotted module name. Usecase suite
      182 passed, 0 failed, 0 skipped.
- [x] red-usecase (the range check's position and its refusal cause) — the premortem's first incident,
      rescheduled from the green-usecase note above because GREEN may not write tests. Two tests: what
      an out-of-range or non-integer probe emits on `document_edit.resolve_owned_revision` — a cause of
      its own or deliberate silence, either way with its extras run through the whole-set rule — and an
      out-of-range number sent at a **foreign or absent** document, asserting the step-1 record is still
      emitted. The second is the load-bearing one: it is what stops the range check from being ordered
      ahead of the document guard, where it would let a caller suppress their own attribution record by
      appending `/0/restore`.
      **Interrupted mid-work-unit and resumed.** The first session hit its API limit during
      `/test-review`; that agent died after dispatching its four detectors and returned no findings, so
      the four files were parked on the remote as the wip commit `f9ab5723` with `[~]` deliberately not
      advanced. The gate was re-run over exactly those four files on resume, before this commit — the
      wip commit is therefore red-phase content that had not passed its gate, not a completed unit.
      Files (wip `f9ab5723`): `backend/usecase/tests/document_edit/test_resolve_owned_revision.py`
      (M, two new tests, 191 lines), `backend/usecase/tests/statements/revision_range_refusal_log_statements.py`
      (new, 179 lines — subclasses `RevisionRefusalLogStatements` so the logger name, message literal,
      `child_id_field` and step-2 cause are reused rather than restated),
      `backend/usecase/tests/statements/refusal_record_shape_statements.py` (M — `_extra_field_names`
      renamed to `extra_field_names` so the whole-set rule and both `EXTRA_FIELDS_AT_STEP_*` sets are
      imported by the new class instead of a second comparison being written), and
      `backend/usecase/tests/document_edit/conftest.py` (M — fixture yields so `stop_collecting()`
      restores the process-global logger level).
      **RED outcome: both tests passed on the first run**, predicted as such — `_parse_in_range` is
      already called *after* the step-1 `try/except` (production lines 89-97) and its failure branch
      returns through `_refuse_at_step_two`, which logs before raising. No disable marker applied.
      Usecase suite 184 passed, 0 failed, 0 skipped.
      **Non-vacuity measured by two mutations, and mutation A sharpened the incident.** Moving the
      `_parse_in_range` block ahead of the step-1 `try/except` failed exactly one test of 184 — the new
      load-bearing one — with `expected (..., 'document-scope-refused')`, got `'revision-scope-refused'`.
      So under that ordering the guard does not merely *lose* the step-1 record: it emits a **step-2**
      record carrying the `document_id` of a document the caller does not own, which is the peer id the
      step-1 cause exists to withhold. Every pre-existing test including all of
      `RevisionNumberRangeStatements` stayed green, confirming the ordering was previously unpinned.
      Mutation B replaced the parse branch's `return _refuse_at_step_two(...)` with a bare
      `raise NotFoundException(REFUSAL_MESSAGE)`; only test 1 failed (`emitted 0 records ... expected
      exactly one`), so the range check's *silence* is attributable to test 1 alone. Both mutations
      reverted; production is byte-identical to HEAD.
      `/test-review` (run on resume) found five holes, and the load-bearing one is that **the
      caller-facing refusal was never asserted on either new path**: `_records_of_probe` called
      `refusal_of` → `captured(...)`, enforcing the exception *type* from inside the act step — an
      invisible behavioural contract, the same defect `revision_number_range_statements.py:48-56`
      records as already fixed for itself — and nothing pinned the 404 *body*. Both tests now go
      through `outcome_of(...)` and assert `assert_is_the_canonical_refusal` in the then phase.
      Two probe rosters were `[0]` slices (one value per kind, silently changing under a reorder):
      widened to all 10 unusable probes, and the unresolvable-document test now crosses both kinds
      against both the foreign and the absent document — 20 cases. A `_assert_roster` comparing
      `tuple(collected)` against the same constant its act step had just iterated was an unfailable
      tautology and was deleted (the indexed loops are the real guard). `_only` was a near-byte-for-byte
      copy of the inherited `_first` and now delegates. And `given_both_guards_have_refused_at_both_steps`
      performed four refusals behind a `given_` name, leaving its test with no visible act phase — split
      into arrange + act. Both tests also gained `assert_neither_document_gained_a_version`.
      **Two fresh mutations after the gate, proving the new assertions are live.** (C) leaking
      `revision_number` into the step-1 body failed the load-bearing test on the new canonical-refusal
      assertion (`NotFoundException('document not found: 0')`). (D) moving only the `int()` parse ahead
      of step 1, leaving the range check behind it, failed **exactly one test of 184 — on probe
      `'abc'`**: this is precisely the hole the roster widening closed, since the old code probed only
      `'0'` against unresolvable documents and `'0'` parses fine, so `/abc/restore` was an unpinned way
      to suppress one's own attribution record. Both reverted; `git diff backend/usecase/src/` empty.
      184 passed, 0 failed, 0 skipped — same count as before the gate, assertions strictly tighter.
      **Three findings reported and deliberately not fixed, all outside the four-file scope:**
      (a) `revision_guard_base.py:52,68-74` seeds revisions directly via
      `revision_repository.seed_revision`, bypassing the write-through-the-writer-usecase rule that
      documents correctly follow via `CreateDocument` — so the guard is proven against revision rows the
      application may never produce. A real violation, but rearranging it touches the whole §1.3 family's
      arrangement; it needs its own decision, not a silent edit inside a gate. (The same seam is already
      recorded at 1.2's `given_a_queued_edit` and at 1.2's adapters-discovery: both wait on 3.1.)
      (b) `revision_number_range_statements.py:81` carries an identical unfailable roster equality to the
      one deleted here. (c) `refusal_log_base.py:100-138` — the new class's step-1/step-2 record
      expectations duplicate the base's; a parameterized `_assert_step_one_record` /
      `_assert_step_two_record` on the base removes it. (c) is `/refactor` territory and was handed to it,
      and applied: `refusal_log_base.py` now owns `_assert_refusal_record(record, cause, document_id,
      which)` with `assert_step_one_record` / `assert_step_two_record` on top, −46 lines across the two
      files. `/refactor` **rejected** (b) with a reason worth keeping: the two roster equalities are not
      identical. The deleted one compared a dict populated by a loop over `UNUSABLE_PROBES` against
      `UNUSABLE_PROBES`; `revision_number_range_statements.py:81` compares a dict **shared across both
      act steps** against a roster passed in per call, so it fails if the wrong roster ran, if the two
      act steps interleave, or if a probe collapses a key — and the indexed loop below it catches only
      the missing-probe direction, never a superset. Do not delete it. It also cleared a stale note in
      this file: the standing `RevisionRefusalLogStatements` duplication is already resolved
      (`refusal_log_base.py` is that extraction; `assert_outage_propagated` / `_outcome_of` /
      `assert_*_lookups` exist in one copy each). One incidental lint fix: a 111-char test method name
      from the wip commit was failing `ruff` E501 on the branch and was renamed.
      **Review passes, both CONCERNS, non-gating — three findings carried, and the first is a live hole
      in this very commit.** (1) `assert_neither_document_gained_a_version` is **vacuous on the
      load-bearing test**: the helper reads `first_document_id` and `second_document_id`, but that test
      probes `foreign_document_id` and `ABSENT_DOCUMENT_ID`. A guard that refuses correctly, emits the
      right step-1 record, and bumps `version` on the *foreign* document on the way past passes all four
      of its assertions — nothing in the suite reads that document's version. The helper's own docstring
      claims to cover "the probed one or the one that actually owns the revision", which is true at its
      original call sites and false at this new one. The same assertion on the first test is correctly
      aimed. Fix it at the next touch of this file. (2) `UNUSABLE_PROBES` is
      `OUT_OF_RANGE + NON_INTEGER` used as **dict keys**, with disjointness unpinned and both rosters
      owned by another file: the day a value appears in both (`"0"` reclassified, `""` or `"-"` moved)
      the key collapses, the case count drops, and every indexed loop still passes — the same
      roster-silently-shrinks defect the widening removed, re-entering through the key type. Wants
      `len(UNUSABLE_PROBES) == len(set(UNUSABLE_PROBES))`. (3) *(premortem)* the load-bearing guarantee
      **is unreachable in production today**: `document_edit_router.py:126` declares
      `revision_number: int`, so every non-integer probe short-circuits to 422 in FastAPI's validation
      phase — ahead of the guard and ahead of `get_current_owner_id` — and emits no record at all. That
      is precisely the suppression this unit believes it closed, and `revision_guard_base.py:30-32`
      states the contrary as fact in a comment. The queued `red-adapter rest` step below names the same
      falsity and is where it goes red; until it lands, the 184-green suite is green about an ordering
      no request can exercise. A fourth, unscheduled anywhere: the range guard is proven only against
      the fake, which has no int4 ceiling — no acceptance test probes `/2147483648/restore` or
      `/abc/restore` against the real column, and `documents_revisions_restore.yaml` requires 404.
- [S] green-usecase (the range check's position and its refusal cause) — **`[S]` verified against the
      diff of the whole RED unit, not against the prediction, and not against a single commit.** The 1.2
      trap at line 358 is that a `/test-review` fix reached across into production *inside the red
      commit*, so a per-commit check would have missed it; here the RED phase spans three commits
      (`f9ab5723` wip, `746feacd` the gated behavior commit, `fd9379ef` the refactor), and
      `git diff --name-only f9ab5723 HEAD -- backend/usecase/src backend/adapters backend/domain
      backend/application` returns **empty**. Zero production files across all three. So `[S]`'s
      condition — no production change to make — holds for the raise, the message and every assertion
      the gate added.
      The reason there is nothing to implement is the RED outcome itself: `_parse_in_range` already
      runs *after* the step-1 `try/except` and refuses through `_refuse_at_step_two`, which logs before
      raising. This step existed to catch the opposite ordering, and the four mutations proved the tests
      would catch it. What the unit bought is a pin, not a behaviour.
- [x] red-usecase (the version guard aimed at the documents the load-bearing test actually probes) —
      **scheduled by the review passes on `746feacd`; the first finding is a live vacuous assertion in
      the committed tests, and GREEN may not write tests, so it is red work.**
      (1) `assert_neither_document_gained_a_version` reads `first_document_id` and `second_document_id`,
      but the load-bearing test probes `foreign_document_id` and `ABSENT_DOCUMENT_ID`. A guard that
      refuses correctly, emits the right step-1 record, and bumps `version` on the **foreign** document
      on the way past passes all four of that test's assertions — no test in the suite reads that
      document's version. The helper's docstring claims to cover "the probed one or the one that
      actually owns the revision", which is true at its original call sites and false at this one. Point
      the guard at the documents each test actually probes (the same assertion on the first test is
      correctly aimed and must stay).
      (2) `UNUSABLE_PROBES = OUT_OF_RANGE + NON_INTEGER` is used as **dict keys** while disjointness is
      unpinned and both rosters live in a file this one does not own: the day a value appears in both
      (`"0"` reclassified, `""` or `"-"` moved) the key collapses, the case count silently drops, and
      every indexed loop still passes — the roster-silently-shrinks defect the widening removed,
      re-entering through the key type. `len(UNUSABLE_PROBES) == len(set(UNUSABLE_PROBES))`, asserted
      where the roster is built.
      Expect a no-red on (2) and a **real** red on (1) only under mutation — the production guard does
      not bump versions, so prove non-vacuity by mutation as this family does, not by expecting a
      natural failure.
      **Outcome: the no-red landed as predicted (184 passed, 0 failed, 0 skipped; predicted type,
      message and count all matched), and then `/test-review` found the fix itself carried the same
      defect one level up.** Re-aiming was not enough. `_assert_versions` compared only the ids the
      caller enumerated, so completeness was a positional accident and a guard that **inserted a row**
      under a freshly minted id was invisible to *every* aim, corrected or not. The helper now builds
      actual from the whole store (`{row.id: row.version for row in ...}`) and compares it to a
      caller-written `dict[UUID, int]` — the row set is inside the equality. That also dissolved the
      `int | None` problem the step was going to introduce: `_version_of` is deleted and the
      `"absent": None` arm with it, because an id **missing from the expected mapping** is one the store
      must not hold at all, which is strictly stronger than `None` — the old arm would have passed
      equally for a document that should have been seeded and never was. A third finding: the roster's
      three indexed walks pinned that no probe was *skipped* but not that no probe was *sent and never
      named*, so a duplicate key dropped a case while every walk stayed green; key-set equality is now
      asserted at the head of all three, the strictness `RevisionNumberRangeStatements` already applied
      over these same rosters.
      **Six mutations across the two agents, and the decisive one is the third.** Bumping the probed
      document's version inside the step-1 `except NotFoundException` branch failed exactly the
      load-bearing test — and under the *same* mutation the committed aim gave 184 passed, so the review
      finding was live and the correction is what closes it. Inserting a row under a fresh id on the
      refusal path also failed exactly one test, but against the **pre-review** assertions it gave
      **184 passed** — re-aiming alone would never have caught it; only comparing the store whole does.
      Appending `"0"` to `NON_INTEGER_REVISION_NUMBERS` is now a collection error naming the repeat,
      and 184 passed with the assert neutered. Dropping one probe from both act-step loops fails 2.
      One mutation is reported as **inconclusive rather than counted**: minting a row for
      `ABSENT_DOCUMENT_ID` does fail the load-bearing test, but through an earlier assertion (the minted
      row makes the id resolvable, so the second probe records the step-2 cause), so that half is
      defended in depth and not independently attributable to the version assertion.
      All mutations reverted; `git diff backend/usecase/src/` empty — no production change in this unit.
      **One deviation kept deliberately, flagged not decided silently:** `_assert_versions` reads
      `document_repository.documents` directly — a storage-port read inside a Statements class, with no
      read-only exemption in the checklist. Both usecase alternatives are strictly weaker: `GetDocument`
      per id reintroduces the enumerated-id blindness this fix removes, and `ListDocuments` is
      owner-scoped and truncates at `DEFAULT_LIMIT`, so it can neither see a row minted under a third
      owner nor guarantee it saw everything. The ports must be fields here regardless, since
      `resolve_owned_revision` takes both as arguments. Not a regression — `_version_of` already read
      the same list — but the honest fix is a whole-store read usecase, which does not exist.
      **Two pre-existing items recorded, both outside this unit's files:** `refusal_of`
      (`revision_guard_base.py:192`) enforces the exception type from inside an act step, the same
      check-15 violation the last gate fixed elsewhere — its only caller is
      `revision_number_range_statements._request_each`; and `revision_refusal_log_statements.py:40-47`
      is three pure rename pass-throughs to inherited base methods. Also still open on the branch:
      E501 on `test_resolve_owned_revision.py:164,178` and a `ruff format --check` failure on
      `revision_silence_statements.py`, both confirmed present on a stashed baseline.
      `/refactor` applied two and rejected three. Applied: `_request_each` no longer calls `refusal_of`
      from inside the act step — it records `outcome_of(self.resolve(...))`, matching the shape its own
      siblings already use, and nothing is lost because both consumers run in every test that calls the
      act step and `assert_is_the_canonical_refusal` pins `(type, str)` together, so "wrong type" and
      "the guard returned a scope" fail there instead; plus the `revision_silence_statements.py` format
      failure. **Rejected, and the first rejection corrects this file:** `refusal_of` has three more
      callers than the brief claimed (`revision_scope_guard_statements.py:44,50,53` and
      `refusal_log_base._records_of:82`), and one of them —
      `test_should_never_touch_the_revision_store_for_a_document_the_caller_cannot_resolve` — makes no
      then-phase canonicality assertion at all, so `refusal_of`'s implicit "something was raised" is the
      only check standing there. Converting it would have silently dropped a real assertion. Also
      rejected: the three pass-throughs at `revision_refusal_log_statements.py:40-47` are Rename Method
      adapters giving the test body scenario vocabulary over a base named in collection vocabulary, and
      the two E501s are `await <fixture>.<method>()` with nothing splittable — every behaviour-preserving
      fix is a rename costing 6 and 15 characters of deliberate meaning, for a column limit.
      **Both review passes CONCERNS. Six findings; the two that converge are scheduled below as their own
      pair, the rest are carried.** Carried: (a) `revision_guard_base.py` landed at **exactly 200
      lines** — the hard cap with zero headroom, so the next `given_`/`assert_` added to the base class
      every revision-guard Statements extends forces a split inside whatever unrelated red step touches
      it; nothing fails at 201. (b) The disjointness assert lives in the module that *consumes* the
      rosters, not `revision_number_range_statements.py`, which defines them **and keys `_refusals` by
      them**; the protection is an import-order accident that vanishes if the downstream module is
      renamed or stops importing. It belongs upstream. (c) The two assert names now undersell what they
      do — `assert_neither_document_gained_a_version` asserts the store holds exactly two rows and
      nothing else, and `assert_no_probed_document_gained_a_version` includes two ids its test never
      probes. Undersold names are how the original vacuity was missed. (d) Prose miscount in the commit
      message: four indexed walks, not three — all four are guarded, only the narrative is off.
- [S] green-usecase (the version guard aimed at the documents the load-bearing test actually probes) —
      **marked late, and the lateness is the record.** When the review passes over `d2186314` scheduled
      the follow-up pair, the new `red-usecase` was inserted *above* this line instead of below it, so
      the next-work-unit rule — first `[~]` or `[ ]` in file order — stepped straight over this step and
      ran the follow-up red. The step was never executed as its own unit and is being closed here, in
      place, rather than back-dated: file order is the only machine-readable part of that rule, and an
      insertion that lands above an open step silently reorders the plan.
      The disposition itself is unchanged by the delay. `d2186314`'s RED touched zero production files
      (`git diff backend/usecase/src/` empty, verified at the time and again across `85d65ff8^..HEAD`),
      so `[S]`'s condition held then and holds now. The unit that jumped the queue also superseded most
      of what a green here could have been about: the two wrappers this step's assertion lived on were
      collapsed into one arrangement-independent statement by `85d65ff8`.
- [x] red-usecase (the version guard extended to the tests and families that still cannot see a write) —
      **both review passes converged here from opposite directions, and the finding is that this unit
      fixed one test of a family-wide blindness.**
      (1) *(agent-review)* The sibling
      `test_should_never_touch_the_revision_store_for_a_document_the_caller_cannot_resolve`
      (`test_resolve_owned_revision.py:53-67`) arranges all three documents, probes the foreign one, the
      absent id **and** the second document, and asserts only refusal canonicality and the revision-store
      call log. The exact mutation this unit exists to catch — a guard bumping the foreign document's
      version on the refusal path — passes it untouched. `assert_no_probed_document_gained_a_version()`
      is directly applicable: same hierarchy, same arrangement.
      (2) *(premortem)* The blindness is a property of the **guard family, not of one test**, and the
      other two families still have it whole: `grep -n version` over `ai_edit_guard_base.py`,
      `ai_edit_scope_guard_statements.py` and `document_scope_guard_statements.py` returns **nothing** —
      no test in either family reads `document_repository.documents` at all, so a guard inserting or
      bumping on the AI-edit or document-scope refusal path passes every assertion they have. That is
      precisely the state `revision_guard_base.py` was in before `d2186314`. The named guard is a peer
      `_assert_versions` on `ai_edit_guard_base.py` with wrappers called from `test_resolve_owned_edit.py`
      and `test_resolve_owned_document.py`.
      (3) *(both passes, independently)* The whole-store equality is **silently coupled to which `given_`
      steps ran**: the expected mapping is hardcoded per method, so adding
      `given_a_document_owned_by_another_account()` to a test for an unrelated reason fails with "a
      document silently moves or appears" — text pointing at production when the cause is the
      arrangement. The cheapest diagnosis is to loosen back toward the enumerated-id form, reopening the
      hole this unit closed. Fix: snapshot `{row.id: row.version}` at the end of the arrangement and
      compare the store to that, keeping the minted-literal `NEW_DOCUMENT_VERSION` check as a **separate**
      statement so the two causes report distinctly.
      (4) *(premortem)* The expected side now pins a store state **production cannot produce**.
      `given_a_revision_recorded_on_the_first_document` seeds revisions 1 and 2 — the file's own comment
      calls them "the two rows the first mutation of a never-edited document writes in one transaction" —
      but a document that has taken that mutation has been through `save_content_if_version_matches`,
      which does `stored.version += 1`, so in production that document is at version **2**. The whole-store
      form pins version 1 as required where the per-id form pinned it only incidentally. This is the
      principle the file already states about the *arranged* side (`:60-61`: a hand-built row can hold a
      shape the application can never produce) applied to the expectation. Advance the version through the
      same port the applied edit uses, and name the post-edit version in both wrappers.
      Expect a no-red on (1) and (2) — production performs only reads — so prove non-vacuity by mutation
      per this family's standard: mutate each family's refusal path to bump and to insert, and show the
      new assertion in that family fails while the old one gave a full green.
      **Outcome: no-red as predicted (184 passed, 0 failed, 0 skipped; type, message and count all
      matched), and the 200-line cap turned out to be the useful constraint.** `revision_guard_base.py`
      had no headroom and findings (1)+(2) needed the same guard in two more families, so rather than a
      third copy the arrangement all three families had duplicated became one class:
      `statements/document_arrangement.py` (172 lines) owns the document store, the two seeding usecases,
      the three ids and the version guard. The three bases shrank — `revision_guard_base.py` 200→111,
      `ai_edit_guard_base.py` 118→90, `document_scope_guard_statements.py` 109→92 — and all three now
      inherit it. New assertions landed in `test_resolve_owned_revision.py` tests 1 and 3 (test 3 is the
      sibling finding (1) named — the one the *previous* unit's own mutation passed untouched), both
      range-refusal-log tests, `test_resolve_owned_edit.py` tests 1 and 2, and
      `test_resolve_owned_document.py`, the last two families having had no version assertion at all.
      **Finding (3) is dissolved rather than patched.** The coupling existed because the expected mapping
      was hardcoded per method; there are now two separate statements —
      `assert_the_arrangement_holds_the_minted_versions` (snapshot vs the literals the `given_` steps
      named) and `assert_no_document_gained_a_version` (store now vs snapshot) — and the snapshot is
      taken **lazily at the first act**, so no test in three packages has to remember a `given_` step.
      The test that forgot would be the one whose guard wrote. That also retires the previous unit's
      "undersold names" finding: the two old wrappers collapse into one arrangement-independent statement.
      **Finding (4) fixed at the seam it was diagnosed:** `given_a_revision_recorded_on_the_first_document`
      is now `async` and goes through `SaveDocument` — the usecase owning the write an applied edit
      performs — so the document carrying those two revision rows sits at `POST_EDIT_DOCUMENT_VERSION = 2`,
      the state production actually produces, where the expected side previously pinned a version 1 no
      such document can hold. `given_an_edit_queued_on_the_first_document` deliberately does **not**
      advance the version (a queued edit has written nothing), and the guard now keeps that distinction.
      **Seven mutations, six conclusive, and the seventh is the interesting one.** Bump-on-refusal and
      insert-on-refusal were run against each of the three resolvers; each failed only *with* the new
      assertions (3/2/2/1/4 failures) and gave a full 184 green with the two new statement calls stripped
      — the pre-change assertions were blind in every family. Every failure landed on
      `assert_no_document_gained_a_version` and never on
      `assert_the_arrangement_holds_the_minted_versions`, confirming the two causes report distinctly.
      The seventh, bump-on-refusal in `resolve_owned_document`, is **unreachable by construction and
      reported as inapplicable rather than counted**: that refusal branch is reached only for a document
      the caller does not own, and the only write port is the owner-scoped CAS
      `save_content_if_version_matches`, which cannot match such a row — a property of production, not of
      the assertion. Substituted with the same bump on the path that *does* resolve: 6 failures across
      all three families versus a full green without. Two earlier insert runs were **inconclusive and
      discarded, not counted**: a fixed `mutant-key` made the second probe raise `ConflictException`
      instead of `NotFoundException`, so pre-existing assertions failed too and the failure was not
      attributable to the new statement; re-run with `f"mutant-{uuid4()}"` they became conclusive.
      All reverted; `git diff backend/usecase/src/` empty.
      **The gate's load-bearing finding is a hazard the RED phase had already been bitten by once.** The
      `async` conversion produces a silently-empty arrangement at any call site that forgets `await`, and
      pytest reports that as a **warning, not a failure** — red-agent hit exactly this at
      `refusal_record_shape_statements.py:73` (a fifth call site), where a test was arranging against a
      document with no revisions and no applied edit while reporting green. The suite was not configured
      to promote it, so the same bug could recur invisibly; `filterwarnings = ["error::RuntimeWarning"]`
      is now in `backend/pyproject.toml`, verified tolerable across the whole backend unit suite (519
      passed). All six call sites swept clean under the flag. Second gate fix: a docstring on
      `assert_the_arrangement_holds_the_minted_versions` claimed it catches an extra document written by
      a `given_` step. It does not — every document is written by `_seed`, which registers the same id on
      **both** sides of the equality, so a third seeded document agrees with itself. The version half is
      literal-checked and sound; the roster half is self-agreeing. Docstring corrected to point at
      `assert_no_document_gained_a_version` as the statement that sees rows appear, since a comment
      promising a guarantee it does not deliver is how the next reader decides not to add the real check.
      The gate verified the lazy snapshot **empirically** with a throwaway probe rather than by reading:
      a bump after the act fails only the write statement, a `given_` step run after the first act fails
      only the arrangement statement in arrangement words, a test that never acts cannot pass vacuously
      (`arranged()` raises rather than comparing an empty snapshot), and acting twice is idempotent so
      the second act's writes stay inside the guarded window. Every act path in all three families funnels
      through exactly one call site, confirmed by grep across all seven sibling Statements classes.
      **Reported, not dismissed:** the wider backend run is 519 passed / **62 skipped**, all of them
      `adapters/db` integration tests env-gated on "no database listening at localhost:5432". Pre-existing
      and unrelated to this unit — but this branch's db work needs `TEST_DATABASE_URL` pointed at
      `textery_s19` (line 88), so those 62 are not running by default on this host.
      `/refactor` applied one and rejected five. Applied: `assert_edit_lookups` →
      `_assert_edit_lookups` — the extraction left the two bases mirroring each other in everything but
      this, and `RevisionGuardBase._assert_revision_lookups` states the reason it is protected (the
      expectation comes entirely from the caller, so a public form lets any collaborator pass `[]` and
      retire the ordering guard without editing an assertion). No test body reached it. Rejected, each
      with a reason: moving `EPOCH`/`OTHER_ACCOUNT_ID` into the new arrangement (single-consumer today is
      not should-move — `OTHER_ACCOUNT_ID` belongs to a matched literal-id block whose whole value is
      minting from one place, and net lines go up either way); pulling `refusal_of` up (needs an abstract
      `resolve` and the signatures genuinely differ, so it is indirection removing no duplication);
      hoisting `assert_the_cross_document_refusal_is_canonical` (the shared expression is already
      `assert_is_the_canonical_refusal`; what remains is per-family recorded state, and it is pre-existing
      rather than extraction residue); touching the three `capture_the_versions_as_arranged()` call sites
      (that is the lazy-snapshot mechanism); and the two E501s again.
      **Both review passes CONCERNS, and they converged — independently and empirically — on the same
      finding: the `filterwarnings` entry this unit shipped does not do what its commit message claims.**
      `RuntimeWarning: coroutine ... was never awaited` is emitted from the coroutine's `__del__` during
      GC; CPython swallows exceptions raised in a destructor, so `error::RuntimeWarning` never reaches
      the test. pytest's `unraisableexception` plugin re-surfaces it as
      `PytestUnraisableExceptionWarning` — a **different class, not matched by the filter, and still only
      a warning**. Both agents ran the exact bug shape against the committed config and got
      `1 passed, 1 warning`; adding `"error::pytest.PytestUnraisableExceptionWarning"` turns the same
      probe into `1 failed`. So the bug that bit RED at `refusal_record_shape_statements.py:73` would
      still report green today. The entry is not useless (it still catches directly-raised
      `RuntimeWarning`s) — it is simply inert for the class it was added for, and the commit message
      asserts a protection the repo does not have. The deeper miss is named the same way by both passes:
      **no test asserts the guard fires.** Seven mutations were run against the version assertions and
      zero against the harness change, which is the one kind of change that cannot go red on its own.
      Scheduled below. Blast radius checked and clean: `pytest adapters domain application` under the
      committed config is 337 passed, 62 skipped. One caveat for the fix — unraisable warnings fire
      whenever the GC runs, so pytest attributes them to whatever test is executing at collection time;
      pair with a `gc.collect()` in a session-scoped autouse fixture or accept the misattribution
      knowingly. And one footgun now sitting inside this diff: `given_an_edit_queued_on_the_first_document`
      stayed sync while its revision-family sibling became async — two symmetric steps in sibling classes
      with opposite `await` requirements, whose severity is entirely a function of whether the gate works.
      **Two further findings carried, both from agent-review.** (a) *Scope*: of the 21 tests in the three
      files, 6 carry the new pair. `test_should_refuse_a_missing_document_and_a_missing_revision_identically`
      (`test_resolve_owned_revision.py:42`) is a pure double-refusal test whose arrangement is already
      fully in place — it was edited in this very diff, only to add the `await` — and needs nothing but
      the two assertion lines; same for the two refusal-record tests. These are exactly the refusal paths
      the unit argues a writing guard slips past. The premortem judges this redundancy rather than a hole,
      since the absent-id and foreign-id branches are covered by the version-asserting test at line 187 —
      both readings are recorded, and the cheap ones are folded into the step below.
      (b) *Latent*: `resolve_via` takes the repository as a parameter precisely so outage statements can
      pass a **failing** one, but `capture_the_versions_as_arranged()` always reads
      `self.document_repository` — not the store the act used. Harmless today (no outage test asserts
      versions), but this unit's whole design is "the snapshot is automatic so no test has to remember",
      which invites the future outage test that adds the assertion and gets a green comparison of a store
      the resolver never touched.
- [S] green-usecase (the version guard extended to the tests and families that still cannot see a write)
      — **`[S]` verified against the diff of the whole RED phase**, per the discipline established at the
      1.2 trap (line 358) and applied at line 973. The phase spans `85d65ff8` (behavior), `a09ce08e`
      (refactor) and `09b35d1c` (the review-pass record), and
      `git diff --name-only 85d65ff8^ HEAD -- backend/usecase/src backend/domain backend/adapters/*/src
      backend/application/src` returns **empty**. The only non-test backend file touched in the entire
      phase is `backend/pyproject.toml`, which is test-runner configuration rather than production — and
      it is the one change the review passes found **inert** (see the entry above and the red step below),
      so it neither implements behaviour nor counts against the `[S]` condition.
      Nothing to implement because the unit's subject was the *tests'* blindness, not the guards':
      all three resolvers perform reads only, every write path sits behind `save_new` /
      `save_content_if_version_matches`, and none of them calls either. Seven mutations proved the new
      assertions would see a write if one existed. As at line 973, what the unit bought is a pin, not a
      behaviour — and this time the pin was extended to two guard families that had none at all.
- [x] red-usecase (the harness gate that does not bite, and the refusal tests still blind to a write) —
      **both review passes on `85d65ff8` verified this empirically rather than by reading, and the
      finding is that the previous unit's own harness change is inert.**
      (1) `filterwarnings = ["error::RuntimeWarning"]` does not fail a forgotten `await`: the warning is
      emitted from `__del__`, CPython swallows destructor exceptions, and pytest re-raises it as
      `PytestUnraisableExceptionWarning`, which the filter does not match. The fix is to add
      `"error::pytest.PytestUnraisableExceptionWarning"` — but the load-bearing part of this step is that
      **a test must prove the gate bites**, because a harness claim is the one kind of change that cannot
      go red on its own and the last unit shipped it with zero mutations against it. Write the probe
      first, watch it report green under the committed config (that is the genuine RED), then let GREEN
      add the filter entry. Pair with a `gc.collect()` in a session-scoped autouse fixture, or record
      knowingly that unraisable warnings are attributed to whichever test is running when the GC fires.
      (2) The cheap half of the scope finding: add the two assertion lines to
      `test_should_refuse_a_missing_document_and_a_missing_revision_identically`
      (`test_resolve_owned_revision.py:42`) and the two refusal-record tests, whose arrangements are
      already in place.
      (3) The latent snapshot/store mismatch: `capture_the_versions_as_arranged()` reads
      `self.document_repository` while `resolve_via` acts on the repository it was handed, so an outage
      test that adds the version assertion compares a store the resolver never touched. Either capture
      from the repository the act was given, or make the mismatch fail loudly.
      **Outcome: a real RED, the first in this run of units.** Predicted `AssertionError` with message
      "the child pytest exited 0, expected 1 — a call site that forgot to `await` an async given_ step
      left the arrangement empty, and the suite reported it as a pass", status FAILED. Actual: exactly
      that, at `forgotten_await_gate_statements.py:141`, the embedded child transcript ending
      `1 passed, 1 warning` with the swallowed `PytestUnraisableExceptionWarning`. Type, message and
      status all matched; `@pytest.mark.skip` applied to that one test.
      **Both directions verified, as the step required.** Under the committed config the gate test fails
      (child exits 0 — confirmed first with a bare probe, `1 passed, 1 warning`); with
      `"error::pytest.PytestUnraisableExceptionWarning"` added, `2 passed` and the child exits 1 naming
      the coroutine. The entry was then **reverted** — it is GREEN's to land, and
      `git diff backend/pyproject.toml` is empty.
      **Shape:** the gate runs pytest as a **child process against the real `backend/pyproject.toml`**
      (`-c` + `--rootdir`, not a copy — the claim is about *this* repo's config) over a generated probe
      module written under the parent's `tmp_path`, outside `rootdir`, so the parent never collects it.
      It stays green once the filter lands and goes red the day anyone removes it. A second, **unskipped**
      test runs the same machinery on an *awaited* probe and asserts exactly one pass — the non-vacuity
      control that makes the first test's failure attributable to the forgotten `await` rather than to
      the harness. The GC-attribution caveat is **handled rather than recorded**: each probe body calls
      `gc.collect()` itself, so the destructor fires inside the probe's own test instead of wherever the
      collector happens to land.
      **`/test-review`'s severe finding is the one worth carrying, because it is this unit's own defect
      in miniature.** `assert_the_failure_named_the_unawaited_coroutine` — the assertion written
      precisely because "exit code alone is satisfied by any child breakage" — searched the **whole**
      child output, and on today's config the child prints that exact sentence in its **warnings
      summary** while exiting 0. So the assertion passed in the very state the test exists to reject,
      and the exit code was the only live check. A gate about an inert guard shipped with an inert
      assertion of its own. The sentence is now read out of the `FAILURES` section only, with the failing
      test named there too; verified red by direct invocation.
      Four more: `"1 failed" in output` / `"1 passed" in output` were substring checks — `"1 passed"`
      also matches `11 passed`, and neither notices a skip, a second failure or a stray warning; both are
      now a parsed whole-tally equality, which additionally rejects a run where pytest declined to
      execute the `async def` control and reported a skip. `rootdir:`/`configfile:` were pinned by
      substring, so a rootdir merely *starting with* that path passed; whole-line equality now.
      **Hermeticity:** the child inherited `PYTHONWARNINGS`, `PYTEST_ADDOPTS`,
      `PYTEST_DISABLE_PLUGIN_AUTOLOAD` and `PYTEST_PLUGINS` — `PYTHONWARNINGS=ignore::RuntimeWarning` on
      a CI runner would make this gate **permanently un-failable**, and disabling plugin autoload would
      stop pytest-asyncio and break the control; all four are now scrubbed. And the 200-line cap forced a
      split: the report reading became `ChildPytestReport` (banner sections, whole header lines, parsed
      tally), 198 / 83.
      **The exit-1 enumeration was checked rather than assumed:** collection/conftest errors exit 2 or 3,
      usage error 4, no-tests-collected 5 — only a genuine test failure yields 1, and with the FAILURES-
      section fix the failure must now be attributed to the probe test for the forgotten-`await` reason.
      **Part (2)** landed as a no-red and is mutation-proven: making `resolve_owned_revision` write on the
      resolve path gives **6 failed / 43 passed** — all three newly-guarded tests die alongside the three
      that already carried the lines. `test_resolve_owned_revision.py` split 198 → 119 with the
      log/silence/shape tests moving to `test_resolve_owned_revision_records.py` (97) to stay under the cap.
      **Part (3)**: `capture_the_versions_as_arranged` now takes the store the act was handed as a
      **required** argument (all three call sites updated, each verified to pass the right one).
      Snapshotting the substitute is not available — `FailingDocumentScopeRepository` holds no rows — so
      the mismatch **fails loudly** instead, with a message naming the test-infra remedy so it cannot read
      as a production defect. Mutation-proven: adding the two version lines to the outage test, which acts
      on the failing repository, would previously have passed vacuously and now fails with "the act was
      handed a document store other than this arrangement's".
      **A flake found and fixed rather than shrugged off:** the first full run failed the *control* test —
      the child aborted collection with `FileNotFoundError` on an ambient `%TEMP%` path it inherited. The
      child now gets `TMPDIR`/`TEMP`/`TMP` and `--basetemp` inside the parent's own `tmp_path`; stable
      across 5× then 3× repeated runs.
      **Two costs and one process note, recorded not buried.** The gate spends a subprocess pytest per
      run (~2s for the pair) — the only way a harness claim can be asserted from inside the harness.
      `generation_lifecycle_statements.py` is **227 lines**, over the hard limit; already committed,
      untouched by this unit, and needs splitting. And the red-agent ran `git stash -u` in this shared
      checkout to get a lint baseline, with the frontend session live — it verified immediately that
      their work was already committed (`73c5411d`) and the pop restored cleanly with nothing lost, but
      it was an avoidable risk and the reason the file-ownership rule asks for separate worktrees.
      `/refactor` applied four and rejected five. It also **took the out-of-unit cap violation**:
      `generation_lifecycle_statements.py` 227 → 158 by extracting the arrangement half into a new
      `generation_arrangement.py` (101) that the Statements class inherits — the shape
      `revision_guard_base.py` and `ai_edit_guard_base.py` already use, so the fixture name, class name
      and every call site are unchanged and that story's conftest and test class needed no edit. The seam
      is the one the class already had. It also collapsed four verbatim copies of the `GenerateDocument`
      wiring, removed a dead `looked_up_result` accessor, un-did a round-trip re-parse in the gate
      Statements (the loop built `f"rootdir: {…}"` then recovered the key it had just embedded with
      `split(":", 1)[0]`), and cleared a `ruff format` deviation the commit had shipped. **Zero files over
      200 lines anywhere under `backend/usecase/tests` now.** Rejected with reasons: extracting a
      `_child_scratch` property (+4 lines would push the file to 201 — the cap outranks a two-occurrence
      expression), splitting the gate Statements, the two E501s again, and deleting three more unused
      generation-family DSL members — those carry docstrings stating scenario claims, so they read as DSL
      written ahead of a scenario in that story rather than split residue, and deleting them is scope
      creep into another story's design. Flagged for that story's owner instead.
      **Both review passes CONCERNS, and both answered the two questions by *running* them.** The skipped
      RED **will** go green when GREEN lands the filter: with only that entry added to a copy of the real
      config, the probe child exits 1, the tally is exactly `{"failed": 1}`, and the FAILURES section
      carries both the probe test name and the coroutine sentence. And the gate cannot pass for a
      config-surface reason other than the fix — `error::PytestUnraisableExceptionWarning` **alone**,
      without `error::RuntimeWarning`, still gives `exit 0, 1 passed, 1 warning`, so both entries are
      required. One fragility recorded: the terminal exception text does *not* contain the searched
      sentence; it survives only because the chained traceback renders the CPython
      `_warn_unawaited_coroutine` frame, so the assertion depends on traceback rendering depth rather than
      on a stable message.
      **The sharpest finding is the one both passes reached independently: this commit ships a second
      inert guard while its whole subject is an inert guard.**
      `_refuse_a_snapshot_of_a_store_the_act_never_used` (`document_arrangement.py:130-136`) is real
      branching logic — a sticky latch set from `acted_on is not self.document_repository`, read by two
      assertion methods — with **zero test coverage**. The outage families do set the latch today, but
      none of them calls a version assertion, so the `assert` never executes in any run; it was
      mutation-proven once by hand and never again. Dropping either call site or weakening the `is not`
      goes green, returning the outage families to the vacuous-pass state it was written to end.
      A related defect in the same helper: it is called from **both** assertions, but its justification
      holds only for `assert_no_document_gained_a_version` (pre-act snapshot vs post-act rows).
      `assert_the_arrangement_holds_the_minted_versions` compares `_versions_as_arranged` against
      `_minted_versions`, both read off `self.document_repository` and independent of the act's store —
      and because the latch is never reset, a test that acts on the arrangement and *then* on a failing
      store loses a valid arrangement assertion and is told to change its act.
      **Two more, both about the gate's reach.** (a) The probe is written to `tmp_path` and passed by
      absolute path, and the child is launched with `--rootdir` but **no `--confcutdir`** — pytest walks
      conftests upward from the *collected file*, not from rootdir, so none of the repo's eleven
      `conftest.py` files load in the child. What is proven is "must fail a bare run under this config
      file", not "must fail the suite": a future session- or package-scope fixture using
      `warnings.catch_warnings()` / `simplefilter` / `pytest.warns` would blind the real suite while this
      gate stayed green. Latent today (no conftest touches `warnings`). The premortem sharpens the same
      seam into a live hazard: if `tmp_path` ever lands inside the repo — a CI image setting `TMP` into
      the workspace — the child imports the repo's conftests and aborts collection, *and* the parent
      collects the leftover probe on a later run, since `tmp_path` roots persist for three runs under a
      fixed module name. Pin `--confcutdir`, and assert at write time that `BACKEND_ROOT` is not an
      ancestor of the probe path; the "outside rootdir" claim is prose, not an assertion.
      (b) `child_pytest_report.py:33` fuses stdout and stderr with `+` and no separator, while
      `summary_counts()` reads `banners[-1]` — anything the child writes to stderr lands after the final
      tally, and a missing trailing newline merges the last stdout line with the first stderr line.
      Low probability, trivial fix, and it sits under every tally assertion.
      Two stale-prose notes: the commit message says four scrubbed environment variables where
      `LEAKY_CHILD_VARIABLES` lists five, and `gc.collect()` is described as load-bearing when on CPython
      the coroutine is a bare expression-statement temporary whose `__del__` fires at end of statement —
      correct as defensive portability, but not the stated mechanism.
- [x] green-usecase (the harness gate that does not bite, and the refusal tests still blind to a write) —
      both deliverables landed and the premortem's incident was closed by the number, not by prose:
      **`186 passed in 7.04s`, 0 failed, 0 skipped** — the skip count is the acceptance signal, and a
      GREEN that had landed the config entry while forgetting the marker would have read `185 passed,
      1 skipped`. The second `filterwarnings` entry
      (`"error::pytest.PytestUnraisableExceptionWarning"`) went in with the mechanism recorded beside it
      in the config itself — the RuntimeWarning is raised from the coroutine's `__del__`, CPython
      swallows destructor exceptions, and pytest re-raises the swallowed error under a *different*
      warning class that `error::RuntimeWarning` alone does not match — so the next reader cannot delete
      the entry as a duplicate. **Mutation-proven rather than asserted:** with only that line removed the
      gate fails at `forgotten_await_gate_statements.py:160` (`1 failed, 1 passed`), and the unskipped
      control keeps passing throughout, so the failure is attributable to the missing filter and not to
      the harness. The two-entry requirement is now enforced from both sides — the RED already showed
      the new entry alone is also insufficient.
      **two deliverables, and the second is the one a GREEN forgets.** (1) Add
      `"error::pytest.PytestUnraisableExceptionWarning"` to `filterwarnings` in `backend/pyproject.toml`
      — both entries are required, verified. (2) **Remove the `@pytest.mark.skip` from
      `test_should_fail_the_run_when_a_call_site_forgets_to_await_an_async_given_step`.** The premortem's
      incident is that a GREEN which lands the config entry and forgets the marker produces a suite
      **byte-identical in signal** to today's — `185 passed, 0 failed, 1 skipped` — with the guard dead
      forever, and nothing in the repo fails on a nonzero skip count. The acceptance number for this step
      is therefore **0 skipped**, not 1.
- [x] red-usecase (the guard on the arrangement's own guard, and the gate's reach beyond one config file)
      — **scheduled by both review passes over `29779ca0`, which reached it independently: that commit
      shipped a second inert guard while its entire subject was an inert guard.**
      (1) `_refuse_a_snapshot_of_a_store_the_act_never_used` has zero coverage — the outage families set
      its latch but never call a version assertion, so its `assert` executes in no run. A test must
      arrange a foreign-store act and assert both `assert_no_document_gained_a_version` **and**
      `assert_the_arrangement_holds_the_minted_versions` raise with the message naming the test-infra
      remedy, since the latch is read from both.
      (2) The same helper is applied where it does not belong: its justification holds only for the
      post-act comparison. `assert_the_arrangement_holds_the_minted_versions` reads both sides off
      `self.document_repository`, independent of the act's store, and the latch is never reset — so a
      test that acts on the arrangement and then on a failing store loses a valid assertion. Either
      scope the refusal to the assertion it applies to, or reset the latch per act, and pin the choice.
      (3) The gate's reach: pin `--confcutdir` on the child so its conftest walk cannot leave the
      scratch, and assert at write time that `BACKEND_ROOT` is not an ancestor of the probe path — the
      "outside rootdir, so the parent never collects it" claim is prose today. Consider the cheap second
      probe placed *inside* `backend/usecase/tests/` so what is proven is "must fail the suite" rather
      than "must fail a bare run under this config file".
      (4) `child_pytest_report.py:33` joins stdout and stderr with `+`; `summary_counts()` reads the last
      banner, so stderr output lands after the tally and a missing trailing newline merges two lines.
      `"\n".join`.
      **(5)–(7) added by the premortem over `0c5c8624` (CONCERNS), all one shape: the config change is
      global to the whole backend tree while the acceptance evidence covered one module.**
      (5) `error::pytest.PytestUnraisableExceptionWarning` promotes *any* GC-time exception in *any*
      module to a hard failure, and CI runs `pytest` over the whole tree. `domain`, `adapters/rest`,
      `adapters/security`, `adapters/generation_provider` were verified clean (324 passed), but
      `backend/adapters/db` (62 tests, real Postgres, asyncpg, `AsyncEngine` teardown) is unverified
      under the new filter and is the unraisable-prone suite. Run it with Postgres up and pin the
      result before CI is the first place the two-entry filter meets a real database.
      (6) A new failure *class*: unraisables fire at GC time, so a coroutine leaked in test A can fail
      an unrelated test B, which then passes in isolation. `error::RuntimeWarning` alone never
      misattributed. Nothing pins attribution — add a third probe whose leak is in test A and whose
      assertion is that the child's FAILURES section names A, not B (the machinery in
      `assert_the_failure_named_the_unawaited_coroutine` already exists). Note the agent-review pass
      checked this on pytest 9.1.1 and saw correct per-item attribution, so this pins behaviour rather
      than fixes a known break.
      (7) The gate proves what `pyproject.toml` *declares*, and scrubs `PYTHONWARNINGS` /
      `PYTEST_ADDOPTS` / `PYTEST_DISABLE_PLUGIN_AUTOLOAD` from the **child** only. The parent — the
      suite CI actually runs — has no such protection: `PYTHONWARNINGS=ignore::RuntimeWarning` or
      `-p no:unraisable` in a runner env disarms the real suite while the gate stays green. Add an
      in-suite check that the live `config.getini("filterwarnings")` carries both entries and the
      `unraisable` plugin is loaded — the one assertion the child-process shape structurally cannot
      make.
      **Outcome: a real RED — six failures, every one matching the prediction in type, message and
      status.** Four new test modules under `usecase/tests/harness/` (`test_arrangement_snapshot_guard.py`
      54, `test_gate_reach.py` 53, `test_child_report_join.py` 34, `test_live_harness_configuration.py`
      27) over four new Statements. Six tests carry `@pytest.mark.skip` — exactly the six failures — so
      **green-usecase's acceptance number is 0 skipped**, the same discipline the previous step used.
      Full run after `/test-review`: **190 passed, 6 skipped, 0 failed**; ruff and mypy clean; largest
      touched file 146 lines.
      **Deliverable (2)'s open choice is pinned to *scoping*, not latch-resetting:** the refusal belongs
      only on `assert_no_document_gained_a_version`, whose expectation is a pre-act snapshot. Resetting
      per act would make the refusal order-dependent and defeat the lazy snapshot's claim that no test
      has to remember an ordering. The reasoning is in `arrangement_snapshot_guard_statements.py`'s
      module docstring so GREEN cannot pick the other arm by accident.
      **Deliverable (3) proved its own premise wrong in the good direction:** the poisoned conftest one
      directory *above* the probe **was** imported by the child, so the conftest walk really does leave
      the scratch today — the "outside rootdir, so the parent never collects it" prose was not merely
      unasserted, it was false. `--confcutdir` is GREEN's to land.
      **`/test-review` found two more inert assertions, both live in exactly the state they exist to
      reject** — the same defect this whole unit is about, now twice removed. (a)
      `live_harness_configuration_statements.py:43` checked `filterwarnings` by *containment*; the ini
      list applies in sequence and last match wins, so a runner appending `ignore::RuntimeWarning` via
      `PYTEST_ADDOPTS` leaves both required entries present and the suite disarmed. Whole-list equality
      against the literal now. (b) `gate_reach_statements.py:111`'s
      `assert ATTRIBUTION_CLEAN_TEST_NAME not in failures` passed over an empty string — `section()`
      returns `""` when the banner is absent — so it was green on a child that failed nothing *and* on
      one that never ran; it was non-vacuous only because a positive assert happened to precede it, an
      ordering nothing pinned. Fixed by a new `ChildPytestReport.failing_test_names()` parsing pytest's
      `___ name ___` sub-banners, hoisted into the parent assertion so both halves collapse to one set
      equality that cannot pass on an absent section. Mutation-checked, not trusted green: flipping the
      expectation to the clean test's name fails at `forgotten_await_gate_statements.py:113`.
      Two claims asserted nowhere were also closed: the poisoned conftest's `RuntimeError` text is now
      checked directly rather than inferred from the tally, and `act_on_a_store_outside_the_arrangement`
      no longer enforces a contract from the act half — split into `outcome_of` plus a then-phase
      `assert_the_foreign_act_reached_the_foreign_store()`, called from all three bodies. That one is
      load-bearing: a `resolve_via` that quietly fell back to the arrangement's own store would leave the
      latch clear and every refusal assertion in the family would test nothing.
      **Deliverable (5) is NOT done and stays open for GREEN.** The `adapters/db` suite (62 tests, real
      Postgres, asyncpg `AsyncEngine` teardown) could not be run under the two-entry filter — the Docker
      daemon is down (`npipe:////./pipe/dockerDesktopLinuxEngine`) and 5432 is closed, and the
      infrastructure guardrails forbid starting it unasked. This is the premortem's actual incident: the
      filter is global to the whole backend tree, and CI is otherwise the first place it meets a real
      database.
      **A checkout quirk worth carrying:** `git status` did not list 3 of the 8 new files until
      `git update-index --refresh` ran — a stale index on this OneDrive checkout, where files written in
      the same second as an index refresh stay invisible. A commit made without that refresh would have
      silently shipped 5 of 8 files.
      **One pre-existing cap violation, untouched:**
      `backend/adapters/db/tests/statements/verification_code_storage_statements.py` is 209 lines — the
      only file over 200 in the backend tree. Pre-existing lint also unchanged (SIM300 in
      `test_ai_edit_router_di_stubs.py:50`, two E501s in `test_resolve_owned_revision_records.py`), none
      in files this unit touched.
- [x] green-usecase (the guard on the arrangement's own guard, and the gate's reach beyond one config file)
      — lands the four production-side fixes the RED pinned: scope the snapshot refusal to
      `assert_no_document_gained_a_version`, pin `--confcutdir` on the child and refuse an in-tree probe
      path at write time, `"\n".join` the child's two streams, and carry deliverable (5) — run
      `backend/adapters/db` (62 tests, real Postgres) under the two-entry filter once Docker is up.
      **Acceptance number is 0 skipped, not 6.**
      **Both review passes over `500204e4` returned CONCERNS, and both found the same third inert guard —
      inside the very assertion `/test-review` had just "fixed".**
      `live_harness_configuration_statements.py:41-59` reads `self._config.getini("filterwarnings")`,
      which returns the **ini declaration only**. `PYTEST_ADDOPTS` is parsed into `-W` command-line
      filters, which live in `config.option.pythonwarnings` and are applied *after* the ini filters, so
      they win. The assertion's own docstring names the exact scenario it cannot see. Confirmed
      empirically three ways in this repo: with
      `PYTEST_ADDOPTS="-W ignore::RuntimeWarning -W ignore::pytest.PytestUnraisableExceptionWarning"` the
      two live-config tests report **2 passed** while a `RuntimeWarning`-emitting probe under the same
      config goes from 1 failed to **1 passed** — the suite genuinely disarmed with the guard green. The
      containment → whole-list-equality fix closed the "appended to ini" arm and left the "appended via
      cmdline" arm, which is the one that works. GREEN must assert the **effective** state: either
      `known_args_namespace.pythonwarnings` empty alongside the ini equality, or — better — a behavioural
      check that `warnings.warn(..., RuntimeWarning)` actually raises inside the live run, which also
      subsumes the plugin check's intent and covers a `-W` smuggled into `addopts` in `pyproject.toml`.
      Two corrections to the record while there: the plugin half **is** real (`-p no:unraisableexception`
      gives 1 failed / 1 passed), and `PYTHONWARNINGS=ignore::RuntimeWarning` does **not** disarm the
      suite — pytest's `simplefilter("always")` wipes it — so the module docstring overstates that vector
      while understating the one that bites. The `/test-review` paragraph in the step above and the RED
      commit body both record deliverable (7) as closed; it is not, and this note is the correction.
      **The premortem's second incident, independent of the above:**
      `try_to_write_a_probe_inside_the_repository` asserts only that an `AssertionError` was raised and
      matched — and its `finally` calls `shutil.rmtree(..., ignore_errors=True)`, erasing the evidence
      before anything looks at the filesystem. `write_probe` does `mkdir` before `write_text`, so a GREEN
      that puts the guard *after* either call passes fully green while the file really lands under
      `BACKEND_ROOT` — the exact failure the test is named for
      (`assert_the_write_was_refused_before_it_landed` proves only `..._raised` today). Capture
      `IN_TREE_SCRATCH.exists()` and the probe path's existence **inside the `except`, before the
      cleanup**, and assert both False.
      **Two lower-severity notes.** (a) `test_live_harness_configuration.py` only runs in a job that
      collects `usecase/tests/harness/`; a CI job running `pytest adapters/db` alone — the
      unraisable-prone suite of deliverable (5) — gets no arming check at all. If the claim is "the suite
      CI actually runs is armed", the check belongs at a root `conftest.py` session scope, reachable from
      every entry point. (b) The attribution test is the only *unskipped* new test and asserts a
      third-party observation (which item pytest charges an unraisable to) as if it were a harness
      property; it turns red on a pytest bump with no hint that no product code changed. Pin a `pytest`
      lower bound tied to this test, or name the version in the failure text so a red run self-diagnoses.
      **Left alone, reported not fixed:** `verification_code_storage_statements.py` (adapters/db) is 209
      lines, pre-existing and another unit's — the only file over the cap in the backend tree. The full
      backend suite also carries 4 pre-existing `adapters/db` failures, verified identical on a stashed
      clean tree; they need a live DB.
      **Outcome: all five deliverables landed, and the acceptance number was met — 0 skipped, not 6.**
      `usecase/tests/harness` **12 passed**; whole `backend/usecase` **196 passed, 0 failed, 0 skipped**;
      full backend **591 passed, 4 failed** (the four pre-existing `adapters/db` failures).
      (1) `_refuse_a_snapshot_of_a_store_the_act_never_used` now guards `assert_no_document_gained_a_version`
      alone — the scoping arm the RED pinned. `document_arrangement.py` landed at **exactly 200 lines**
      after three rounds of trimming prose back under the cap.
      (2) `--confcutdir <probe dir>` on the child, and `_refuse_a_probe_inside_the_repository` is the
      **first statement** of `write_probe`, ahead of both `mkdir` and `write_text`, comparing resolved
      ancestry (`BACKEND_ROOT not in probe_path.resolve().parents`) rather than a string prefix so a
      symlinked or 8.3-short scratch cannot slip past.
      (3) `"\n".join((stdout, stderr))`, mutation-checked: reverting to `+` fails both
      `test_child_report_join.py` tests.
      (4) **Deliverable (7) is genuinely closed this time, and verified against all three vectors.** The
      live check now asserts the *effective* state before the `getini` equality:
      `config.option.pythonwarnings` is empty, and a real `RuntimeWarning` is provoked and must raise.
      With `PYTEST_ADDOPTS="-W ignore::RuntimeWarning …"` the pair goes from 2 passed to **1 failed /
      1 passed**; with `-W ignore::RuntimeWarning` smuggled into `addopts` inside `pyproject.toml` —
      the vector neither the ini read nor the env scrub can see — **1 failed**; and weakening the ini
      entry to `always::RuntimeWarning` fires the behavioural probe with its own message, so it is not
      dead weight. Tree restored after each.
      (5) **Deliverable (5) closed, and it answered its question.** Docker was already up with
      `infra-postgres-1` healthy (nothing started). `adapters/db` under the two-entry filter: 62 tests,
      **58 passed, 4 failed** — all four the documented `TestFindScopeByIdAndDocument` failures whose root
      cause is `asyncpg.exceptions.UndefinedTableError: relation "ai_edits" does not exist`, the table the
      `adapters-discovery` gate's inserted `red-adapter db` step is scheduled to write. **No
      unraisable-warning failure and no misattribution appeared** — which is the whole question the
      deliverable existed to answer, and the premortem's incident is closed by that number.
      **One gap GREEN could not close, carried forward:** the premortem's point that
      `assert_the_write_was_refused_before_it_landed` proves only `_refusal is not None` — its `finally`
      rmtree erases the filesystem evidence — needs a *test* change, and tests are read-only in GREEN.
      Verified out-of-band instead (driving `write_probe(IN_TREE_SCRATCH, "")` directly: refusal raises,
      `IN_TREE_SCRATCH.exists()` is `False`, no leftover under `harness/`). The guard is correct today,
      but the test would not notice a later edit moving it after the `mkdir`.
      **A shared-checkout mistake, recorded not buried:** the green-agent ran one `git stash`/`git stash
      pop` pair for a lint baseline while the frontend session was live, and two frontend files changed
      under it during that window. The pop applied cleanly and `git stash list` holds only an unrelated
      old entry, but this is the second unit in a row to do it — the file-ownership rule asks for
      separate worktrees for exactly this reason.
      Not addressed, outside this step's five deliverables: the root-`conftest.py` placement of the
      arming check so a `pytest adapters/db`-only CI job is covered too, and the `pytest` lower-bound pin
      on the attribution test.
      **`/test-coverage` had to be pointed by hand, and the carryover quirk held.** Every file this unit
      changed lives under `usecase/tests/`, not `src/`, so the default `--cov=usecase/src` reported
      nothing and `git diff HEAD --name-only -- 'backend/*/src/'` was empty — a **fifth** false all-clear
      on this story, avoided only by naming the files. It also showed why the subset matters:
      `document_arrangement.py` reads 89% under the harness tests alone and **100%, 4/4 branches**, under
      the full module, so the rescoping is covered on both arms. Hand-checked the conditionals coverage.py
      cannot see (`try/except` and `assert` are not branches):
      `_refuse_a_probe_inside_the_repository` is genuinely 2/2 — the `return` arm on every normal
      `write_probe`, the `raise` arm in the in-tree refusal test. Two real gaps got red/green pairs below.
- [x] red-usecase (coverage: disarmed suite drives the arming probe red) — **the newly-written core of
      this unit has an unproven negative arm.** `live_harness_configuration_statements.py:97` — the
      `raise AssertionError` closing `_assert_a_runtime_warning_actually_raises` — has never executed, and
      coverage reports **0 branches** for the whole file, so the `L97` line number is the only signal
      there is. The docstring's evidence (2 passed → 1 failed under `PYTEST_ADDOPTS`) was measured **by
      hand at the terminal, not by a test**, so nothing in the suite would notice if the `except` clause
      were widened to `Exception` or if a future pytest stopped turning the warning into a raise.
      `_assert_no_command_line_filter_overrides_the_declaration`'s `assert overrides == []` is the same
      shape and equally invisible. Drivable with machinery this scenario already owns: run a child over a
      probe that calls the statement **with** `PYTEST_ADDOPTS="-W ignore::RuntimeWarning"` left in the
      environment — which needs a `ChildPytestRun` variant that does not scrub `LEAKY_CHILD_VARIABLES`
      (scrubbing is unconditional at `child_pytest_run.py:137-139`). That is a real design cost, and it is
      also precisely the claim in this step's own title.
      **Outcome: a real RED — 2 failed, 1 passed, prediction matched in type, message, site and status.**
      `test_disarmed_arming_probe.py` (57) over `disarmed_arming_probe_statements.py` (140), plus one
      conftest fixture. Three tests, three environments, and **the two arms need two different vectors
      because each is invisible to the other**: the override check runs *first*, so
      `-W ignore::RuntimeWarning` short-circuits before the behavioural probe and can never reach L97.
      `-p no:warnings` leaves `config.option.pythonwarnings` empty and `getini` intact, so only the
      provoked warning sees it — that is the vector for L97. The third test is a live positive control
      (env deleted), deliberately **not** skipped: a passing coverage test left skipped covers nothing.
      Each failure is pinned three ways — whole tally + exit code, the whole *set* of failing test names
      (so an absent FAILURES section cannot pass), and the arm's own sentence scoped to FAILURES. The
      expected sentences are **literals, not read back from the module under test**: read back, they
      would still pass with both messages blanked.
      **The fifth inert guard was caught in review, and it was inside the RED itself.** Each `given_`
      scrubbed only `PYTEST_ADDOPTS`, so each test differed from the control by more than the vector it
      is named for — and the one that matters is `PYTHONWARNINGS`, a genuinely distinct mechanism:
      `-W` filters land in `config.option.pythonwarnings`, while `PYTHONWARNINGS` is consumed by Python's
      own warnings machinery before pytest sees anything. An ambient `PYTHONWARNINGS=ignore::RuntimeWarning`
      stops the provoked RuntimeWarning from raising *by itself* — exactly the state
      `test_..._unloads_the_warnings_plugin` asserts — so that test would have gone green with
      `-p no:warnings` contributing nothing. Inert only while `ChildPytestRun` still scrubs
      unconditionally; **live the moment this step's GREEN lifts that scrub, which is the whole point of
      the step.** Fixed by deleting every name in `LEAKY_CHILD_VARIABLES` (imported, not relisted, so the
      isolation cannot fall behind the scrub it replaces) before setting the single vector variable.
      **Two detector proposals rejected as inert in turn:** mutual exclusion of the two refusal sentences
      (only one arm can raise per test, so the negative is green whenever the positive is, and it cannot
      fail while its partner passes), and control negative pins (their stated rejected state — a probe
      whose body did nothing — yields `{"passed": 1}` and no refusal sentences, so the assertion stays
      green in precisely that state).
      **The discriminator carrying the second vector is load-bearing and unobvious, now documented in
      place:** `-p no:warnings` unloads the plugin that *records* warnings, so the tally is exactly
      `{failed: 1}`, whereas a `pyproject.toml` that merely lost its `filterwarnings` entries leaves that
      plugin loaded and reports `{failed: 1, warning: 1}`. The whole-dict tally pin is the only reason
      that second state is red — do not weaken it to a bare `failed` count.
      **GREEN is satisfiable, verified out-of-band before the markers went on:** both vectors driven by
      hand against the real config with the env kept, each firing its exact pinned sentence in FAILURES,
      `1 failed`, exit 1. GREEN's only work is the one the step names — give `ChildPytestRun` a way to
      keep the ambient environment for this family, leaving the unconditional scrub in place for the
      forgotten-await gate, whose whole claim depends on it. Wiring the `given_` steps to that opt-in is
      permitted setup work; **no assertion may change.**
      Suite: **197 passed, 2 skipped, 0 failed** — the 2 skips are exactly the two RED tests, so the next
      step's acceptance number is **0 skipped**. ruff, ruff format and mypy clean on all three files.
      **Two structural findings deferred to `/refactor`** (they change committed shared files):
      `_assert_the_arming_check_failed_saying` duplicates the base's `_assert_the_failure_was_charged_to`,
      which was parameterised "for a family whose probe fails elsewhere" yet still hardcodes
      `UNAWAITED_COROUTINE_TEXT`; and `DisarmedArmingProbeStatements` subclasses
      `ForgottenAwaitGateStatements` for the child-run machinery and thereby inherits four public DSL
      steps that are false for this family — the machinery wants extracting into a shared
      `ChildProbeStatements` base.
      **A coupling worth carrying:** the probe imports `statements.live_harness_configuration_statements`
      and resolves it only because `pythonpath` in `backend/pyproject.toml` lists `usecase/tests` and the
      child runs with `--rootdir backend`. Dropping that entry breaks this family with a
      `ModuleNotFoundError` that reads as a harness defect rather than a config change.
- [~] green-usecase (coverage: disarmed suite drives the arming probe red)
- [ ] red-usecase (coverage: bannerless child report tallies empty) — `child_pytest_report.py:133-134`
      (`if not banners: return {}`) is a partial branch, False arm only. It matters because that empty
      `{}` is the exact symptom the `"\n".join` change was written to prevent — the docstring names it
      ("the tally then read `{}` while the gate blamed pytest for it"). The fix landed; the symptom path
      itself has still never been executed, so a report with no banner lines at all has never been fed
      through `summary_counts()`.
- [ ] green-usecase (coverage: bannerless child report tallies empty)
- [ ] red-usecase (the half of the join that was never fixed, and the half of the arming never probed) —
      **scheduled by both review passes over `74810821`, which converged on the first item
      independently.** The agent-review pass hunted the fourth-inert-guard question *empirically* and
      found none — it drove `PYTEST_ADDOPTS="-W ignore::RuntimeWarning"` red, drove `-p no:warnings` red
      (a vector **only** the behavioural half can see: `pythonwarnings` empty, `getini` still exactly the
      two entries, so the probe is not dead weight), reproduced `--confcutdir` standalone (without it the
      poisoned parent conftest is imported at collection), and confirmed the ancestry comparison is
      resolved-vs-resolved. All three new guards are armed. These are the gaps beside them.
      (1) **`"\n".join` closed the second of the two consequences its own RED spec named, not both.**
      `child_report_join_statements.py`'s docstring lists them: stderr landing *after* the final tally
      banner so a banner-shaped stderr line becomes the last one `summary_counts()` reads, and the merged
      last line. Only the second is fixed. A banner-carrying stderr line still becomes `banners[-1]` —
      precisely the "the gate blames pytest for it" failure the unit set out to end — and no guard can
      exist under the current fixture, because `STDERR_NOISE` was deliberately chosen to carry no banner.
      Needs a third join statement with a `=+ … =+` line on stderr, asserting the tally is still read off
      the stdout banner and `section(FAILURES_SECTION)` still returns its real body.
      (2) **The behavioural arming probe covers one of the two required entries.** The file states plainly
      that `error::RuntimeWarning` and `error::pytest.PytestUnraisableExceptionWarning` are each
      insufficient alone, but `_assert_a_runtime_warning_actually_raises` provokes only the first. Its own
      docstring names the vector it exists for — session-time plugin meddling
      (`resetwarnings()`/`simplefilter("ignore")` after config load) — which is class-agnostic and
      disarms both equally, while the unraisable half is only declaration-checked (`getini`) and
      registration-checked (`hasplugin` stays True while the warning it produces is ignored). So under
      the exact scenario the probe was written for, the RuntimeWarning half raises green and the
      unraisable half is silently off. The symmetric `_assert_an_unraisable_warning_actually_raises` does
      not exist.
      (3) **The in-tree refusal is anchored to `backend/` while its message claims the repository.**
      `BACKEND_ROOT = Path(__file__).resolve().parents[3]`, but the refusal says "write the probe to a
      tmp_path outside the repository". A CI image or `--basetemp` putting temp at `<repo>/.tmp` —
      inside the repository, outside `backend/` — passes the guard and leaves a collectable `test_*.py`
      for any root-scoped run. `gate_reach_statements.py:16-18` already anticipates that CI scenario in
      prose. The existing refusal test only exercises a path already under `backend/`, so the anchor
      choice is untested in the one place it differs from the claim. Pin the anchor and the message to
      the same tree.
      (4) Three prose defects the passes found in the diff, all cheap: `test_arrangement_snapshot_guard.py:11-13`
      still says the refusal "guards every version assertion in three guard families" — this very commit
      made it guard exactly one, and the file's last two tests prove the opposite of the sentence above
      them. The `assert_both_filter_entries_are_in_force_in_this_run` docstring credits the behavioural
      probe with covering a `-W` smuggled into `addopts`, which is false — pytest merges `addopts` and
      `PYTEST_ADDOPTS` into one arg list during `_preparse`, so `config.option.pythonwarnings` sees it
      and the *first* check catches it; the prose understates its own coverage and mis-maps the vectors
      for whoever later trims a "redundant" check. And `_refuse_a_probe_inside_the_repository`'s docstring
      claims "`resolve()` on both sides" while the code resolves only `probe_path` — correct today solely
      because `BACKEND_ROOT` happens to be resolved at its definition 20 lines up, and silently inert the
      day that changes.
- [ ] green-usecase (the half of the join that was never fixed, and the half of the arming never probed)
- [ ] red-adapter rest (the restore route declares its revision number as a string) — **the guard's
      docstring asserts a fact about the route that is false as shipped.** It says "the route declares
      the parameter as `str` precisely so that FastAPI does not answer it 422 ahead of the Bearer
      dependency"; `document_edit_router.py:126` declares `revision_number: int`. So
      `POST /documents/{id}/revisions/abc/restore` **with no Bearer token** returns 422 today — path
      coercion fires ahead of `Depends(get_current_owner_id)` — which is both the disclosure the ADR's
      non-integer row forbids and the reason the guard takes a `str` at all. The guard's entire
      non-integer branch is unreachable through the real route. Note that `ai_edit_routes.py:19`
      actively pins the int shape (`PROBE_REVISION_NUMBER = 1`), so a rest-layer test has to *change*
      for the ADR to become true — this is not an additive step.
- [ ] green-adapter rest (the restore route declares its revision number as a string)
- [ ] adapters-discovery — **three ADR-forced schema pins are binding on this gate and are owned by no
      other checkbox** (both passes found this independently, and the ADR itself records that 1.2
      shipped its FK and PK unpinned). None of the gate's three standard checks asks for them, and
      there is no `red-adapter db` step scheduled for 1.3 yet — this gate must insert one and carry all
      three into it. (1) The range constant and the declared column type must be pinned **together**:
      `LARGEST_VALID_REVISION_NUMBER` is a hard-coded `2147483647` and the table is unwritten, so
      `SMALLINT` sends legitimate values to the driver as a numeric-out-of-range error, past the narrow
      `except`, out as the one status the restore contract forbids — while `BIGINT` opens a silent dead
      band of storable values refused as 404. All twelve tests stay green either way. (2)
      `UNIQUE(document_id, revision_number)`, whose absence turns `one_or_none()` into
      `MultipleResultsFound` — the same 500-on-the-guard-path class by a different door, and one the
      usecase layer is structurally blind to because the fake's `next(...)` silently returns the first
      match. (3) The FK `ON DELETE CASCADE`. (4) **Added by the premortem on `dacecdb0`: the finder's
      `WHERE` is scoped by `document_id`.** The guard returns the repository's answer unchecked — there
      is no `scope.document_id == document_id` assertion between the port and the caller — so the entire
      cross-document property rests on one `WHERE` clause in an adapter that does not exist yet, and
      `revision_number` reads as a natural key, which makes `WHERE revision_number = :n` the plausible
      mistake. `FakeDocumentRevisionRepository` filters on both fields and is the only thing that has
      ever enforced the clause; the ADR names this failure class and mitigates it by putting `id` on the
      scope, not by pinning the filter. The `red-adapter db` test must seed the **same** revision number
      on two documents owned by different accounts and assert the finder returns the requested
      document's row and `None` for the other.
      (5) **Added by both passes on `56878c76`, independently: the port-shape half of 1.2's pair has no
      revision equivalent.** The stub guard this work unit shipped proves the raising body *executes*,
      but `ai_edit_port_shape_statements.py:70` records that it can never fire for a real adapter —
      adapters satisfy these Protocols **structurally** and are forbidden from inheriting them, so the
      inherited body protects nothing in production. What 1.2 added to cover that gap
      (`backend/adapters/db/tests/statements/ai_edit_port_shape_statements.py`: adapter not in the
      Protocol's MRO, finder present in the adapter's own `vars()`, `iscoroutinefunction`, and an exact
      hand-written positional signature) has **no revision counterpart** — no
      `SqlAlchemyDocumentRevisionStorage` exists under `backend/adapters/db/src/` and no step schedules
      one. The `red-adapter db` step this gate inserts must carry a
      `document_revision_port_shape_statements.py` mirroring all four assertions. Aggravating: the
      restore route's revision number is a `str` at the boundary (see the rest-adapter pair above), so
      mypy's int/UUID distinction will not backstop a transposition or coercion drift the way it partly
      does for 1.2.
      (6) **The port's keyword-only contract is unpinned, and deleting the `*` is a silent no-op.** The
      new stub test pins the method name and the message but calls the body by keyword, which succeeds
      whether or not the `*` is there; 1.2's `assert_the_scoping_ids_are_keyword_only` asserts it for
      the **port** as well as the adapter, and the 1.3 mirror inherited the three hardenings but not
      this one. Pin `inspect.signature(DocumentRevisionRepository.find_scope_by_number_and_document)`
      as exactly `[("self", POSITIONAL_OR_KEYWORD), ("revision_number", KEYWORD_ONLY),
      ("document_id", KEYWORD_ONLY)]`, hand-written and positionally exact, per the
      `EXPECTED_FINDER_SIGNATURE` precedent.
      **Read (5) and (6) together with this secondary effect the premortem named:** the stub guard
      drives `document_revision_repository.py` to 100%, so no future coverage pass will surface that
      module again — and what the 100% now hides is that the port has *zero* production implementation.
- [ ] green-acceptance

### Scenario 1.4: A malformed revision number is refused as not found, never as a server error
- [ ] red-acceptance
- [ ] design — **carries one decision handed over by 1.3's ADR** (edge-case table, "parseable but not
      plain ASCII digits"): `_parse_in_range` delegates to `int()`, which accepts surrounding
      whitespace, a leading `+`, PEP-515 underscores and any Unicode decimal digit, so `" 2"`, `"+2"`,
      `"1_0"` (→ 10) and the Arabic-Indic `"٢"` all resolve real revisions. 1.3 deliberately did not
      form the opinion and 1.4's checklist did not pick it up either, so it was scheduled to be formed
      by nobody. Nothing cross-tenant — the document scope still holds — but the endpoint is URL-aliased,
      which matters the moment anything downstream caches, rate-limits, dedupes or audits by path, and
      §7's list route inherits the same parser. Pin the roster
      `(" 2", "2 ", "+2", "1_0", "٢", "2
")` to one decided behavior and record it back in the ADR.
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: An absent selection means whole-document, an explicit null does not
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A missing or zero base version is refused before any row is written
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: A stale base version is refused as a conflict
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4: A blank or over-long instruction is refused, measured in code points
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.5: A missing idempotency key is refused before any row is written
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.6: A whole-document edit above the context-fit threshold requires a selection
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.7: Server-owned fields in the body are ignored, not honoured
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: An accepted instruction queues an edit without mutating the document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Replaying the same key with the same body returns the same edit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: Reusing a key with a different body is refused, never silently ignored
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Re-executing the worker job for one edit produces one of every side effect
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: An edit that applied its change but died before its terminal event does not reapply
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Backend Scenarios — Lifecycle and Streaming (01_API_Tests_Lifecycle.md)

### Scenario 4.1: A second edit on a document with a live edit is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: Cancelling a live edit terminalises it with no side effect
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: A provider result arriving after cancellation cannot commit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: Terminal states are absorbing and illegal transitions are rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: An edit abandoned by a dead worker is reclaimed and never locks the document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.6: A committed edit whose enqueue was lost is still executed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: A stream emits ordered chunks followed by exactly one terminal event
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: Reconnecting replays the tail with no gap and no duplicate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Reconnecting at the last known event still terminates the stream
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: An unusable last-event value replays from the start rather than failing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: Chunk text cannot forge stream framing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6: A chunk boundary inside a multi-code-unit character does not corrupt the text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.7: A failure arrives as a terminal error event, never as a dropped connection
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Backend Scenarios — Apply, History and Quota (01_API_Tests_Apply.md)

### Scenario 6.1: The document, revision, message and terminal event commit as one unit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2: A client that sees done immediately observes the version it was told
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.3: A manual save racing an AI edit on one version leaves exactly one winner
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.4: A worker whose base version no longer matches writes nothing and refunds
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.5: A result over the content limit fails the edit rather than truncating
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.6: A selection-scoped edit rewrites only the selected range
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.7: Model output is sanitised before it is persisted or streamed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.8: A selection-scoped result is sanitised against the spliced document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1: A document with no history returns valid empty pages
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.2: The first mutation records the pre-edit content as a restorable revision
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.3: Restoring a revision creates a new version and destroys nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.4: A double-clicked restore creates exactly one new version
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.5: List endpoints are bounded, ordered and content-free
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.6: The daily quota is enforced, charged once and refunded once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.7: The quota day boundary follows the configured clock, not the caller's
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.8: A quota store that cannot be read denies the request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Backend Scenarios — Hazard Guards (01_API_Tests_Guards.md)

### Scenario 1.1: Multi-byte content survives a store-and-read round trip byte for byte
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Normalisation happens before measurement and before offsets are applied
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: Machine-readable values are produced under an invariant locale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: A retried attempt does not leave the previous attempt's chunks in the tail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: Replaying a key whose edit is already terminal has a defined outcome
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: A quota charge is released when the submission transaction rolls back
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4: A refund and its terminal state commit together
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: An edit accepted on one instance streams and cancels from another
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A committed event reaches an already-connected reader within the stated window
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: A restore losing to a manual save is refused, not silently applied
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: A manual save during a live edit succeeds and makes the edit lose
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: Cancel and worker completion resolve to exactly one terminal state
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.6: An edit cancelled before pickup costs no provider call
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.7: The same key on a second document creates a second edit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Backend Scenarios — Hazard Guards (continued) (01_API_Tests_Guards2.md)

### Scenario 4.1: Illegal transitions between non-terminal states are rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: An unknown constant follows the stated policy rather than being coerced
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: An unknown field on the wire is ignored rather than rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: A malformed page size is refused, an omitted one defaults
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: An empty or forged cursor is refused, not treated as the first page
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.7: A blank idempotency key is refused like an absent one
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.8: The event tail is served by its index, not by a scan
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.9: A non-terminal edit reports progress, not a frozen zero
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: An unlisted ordering parameter is not honoured
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: The idempotency key is bounded
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: An oversized request body is refused before its fields are parsed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6: Equal sort keys page in a stable total order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: The reaper reclaims at the deadline and not before
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2: The quota becomes available exactly at the reset instant it advertises
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

**Deferred: Scenario 1.1 green-acceptance** — re-scheduled here by the 2026-07-31 decision (see
Scenario 1.1 above). Deliberately placed at the tail of every backend scenario section, not next to
1.1: the next-work-unit rule is "first `[~]` or `[ ]` in file order", so prose saying "runs last"
buys nothing unless the position agrees. It runs after the scenarios owning the message and revision
read paths (4.x revisions, 6.x messages) have landed their usecases, migrations and router mounting —
the aftermath assertion needs `GET /messages` and `GET /revisions` answering
`200 {"items": [], "next_cursor": None}` for the rightful owner, which a refusal-only guard cannot
satisfy. Not a `###` heading, so it does not inflate the scenario count in `stories.md`; Scenario 1.1
counts as done because its own checklist is fully `[x]`/`[S]`, and this line is the one step it owes.
Nothing else in 1.1 is outstanding.
- [ ] green-acceptance (Scenario 1.1) — remove the class-level disable marker on the AI-edit guard
      acceptance test and run it; production code is out of scope for this step. Before starting,
      re-read the four blockers recorded at Scenario 1.1 and confirm each is now false.

**Deferred: Scenario 1.2 green-acceptance** — same wall as 1.1, reached from the other side, and
re-scheduled here for the same reason: file order is the only machine-readable part of the
next-work-unit rule. Re-verified at the step rather than inherited from the note — `main.py:116-119`
mounts generation/auth/oauth/document and not `document_edit_router`; `usecase/src/document_edit/`
holds the guard helper, the port and the scope and none of the seven usecases; and no file under
`application/src` mentions `document_edit`, so nothing is wired even if it were mounted. 1.2 needs
strictly more than 1.1: its setup queues a **real** edit through `POST /ai-edits` (a fabricated id
would be refused by any handler that merely fails to find it, and the path document id would never
be consulted), so it waits on **3.1** for `QueueAiEdit`, and its aftermath read
(`GET /ai-edits/{edit_id}` under the edit's own document, whole-body) waits on the state endpoint in
**4.x**. Everything 1.2 owns is done: the guard, its five forced guards, the port, the schema and
the finder. This line is the one step it owes.
- [ ] green-acceptance (Scenario 1.2) — remove the class-level disable marker on the cross-document
      acceptance test and run it; production code is out of scope for this step. Before starting,
      re-verify the three blockers above against the tree rather than trusting this note.

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1: A provider response becomes a revision, a reply and a terminal event
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: A provider reply that changes nothing is still a completed edit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Each provider failure ends the edit with its own terminal code
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A server-side provider failure is retried, a client-side one is not
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: Provider timeouts are finite and configured
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A job dequeued before its row is visible retries rather than failing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Two reaper activations do disjoint work
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: The existing generation flow keeps working alongside the new worker
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: A rolled-back submission never leaves a job behind
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: A retry is sized to the remaining deadline, not to a fresh timeout
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: A poison edit does not block healthy edits behind it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: A reaper that dies holding its lease does not stop reclamation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: The prompt's conversation window is bounded
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.6: A runaway provider is abandoned at the limit, not buffered whole
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1: Every endpoint is owner-scoped and leaks no existence
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Identifiers from a sibling resource are rejected, not silently accepted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: A stale document reference cannot outlive its version
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Injection payloads in the instruction reach the datastore as data
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: Instruction and selection bounds are enforced in code points
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: A forged log prefix in the instruction produces one log record
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4: Server-owned fields cannot be set from the body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Model output is neutralised before it is stored or displayed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Model output cannot forge stream events
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: No error path discloses internal detail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: The daily quota cannot be exceeded by racing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: A single document cannot be driven into parallel edits
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: Every authentication failure looks the same on every endpoint
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: The cancel endpoint binds nothing from its body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: An instruction cannot forge the provider's own message structure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: Every failure family returns the sanctioned error shape
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: A successful edit does not leak the document into the logs
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: Edit submission sustains the configured request rate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Provider calls stay within the downstream rate limit under submission load
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Concurrent event streams stay within the connection and pool bounds
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: Aborted streams return connections to baseline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Steady-state event polling is spread across the interval
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Failure paths release their resources as reliably as the success path
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: Exhausting the stream and pool ceilings rejects, never hangs
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Pathological content does not stall the apply path
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1: A datastore outage refuses edits cleanly instead of hanging
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Edits work again after the datastore recovers, with no state left behind
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: A broker outage does not accept edits that will never run
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A worker started against a recovered broker drains the backlog without a stampede
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Missing or invalid configuration fails at startup, in both processes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A non-development environment refuses to boot with the fake edit provider
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: The timer ordering invariant is validated at startup
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: The proxy streams the first chunk before the response completes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: A silent stream is kept alive rather than dropped
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios — Hazard Guards (04_Infrastructure_Tests_Guards.md)

### Scenario 4.1: A missing threshold or quota setting fails closed, never open
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: A batch that fails on one item still processes the rest and names the failure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: Every degraded path emits an attributable signal and the healthy path emits none
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: A reaper that stops running is detectable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: Pruning with an absent or zero retention bound affects no rows
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.6: Deleting an edit leaves no orphaned events
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.7: A record written before this feature reads back with defined defaults
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.8: Revision history has a stated growth bound
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.9: A request for a new path landing on an old instance degrades, never errors
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
