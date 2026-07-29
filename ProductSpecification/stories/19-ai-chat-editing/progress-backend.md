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
- [~] green-acceptance — **BLOCKED, and not by anything green-acceptance is allowed to change.**
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
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: A revision belonging to another document of the same owner is not found
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4: A malformed revision number is refused as not found, never as a server error
- [ ] red-acceptance
- [ ] design
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
