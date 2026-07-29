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
- [ ] red-adapter db — save through `save_new`, read back through `find_scope_by_id_and_owner`
      against the real schema: the owner's own document resolves to its scope, another account's
      does not, an absent id does not. The positive control is the point — a port method inherited
      from the Protocol returns `None` for every input (the bodies are `"""doc"""` + `...`, which is
      a concrete coroutine, not an abstract declaration), so a storage that "implements" the port by
      inheriting it would refuse every user their own documents while mypy and the usecase suite
      both stay green. Assert the SELECT does not read `content`.
- [ ] green-adapter db — implement the bounded SELECT. Also close the shape that makes the above
      failure silent: the Protocol bodies must `raise NotImplementedError` rather than `...`, and
      `backend-ci.yml` needs a mypy step (the config already exists in `backend/pyproject.toml` and
      would go red on this commit today).
- [ ] red-adapter rest — the seven AI-edit routes, each delegating to a usecase whose first
      statement is `resolve_owned_document`. Per the ADR the refusal must precede validation and
      version checks: a foreign document with a malformed instruction is 404, never 422; with a
      would-have-been-correct `base_version` it is 404, never 409; and `.../stream` answers plain
      non-streaming JSON, never a 200 `text/event-stream` carrying an error frame.
- [ ] green-adapter rest — wire the routes and the usecases.
- [ ] green-acceptance

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
