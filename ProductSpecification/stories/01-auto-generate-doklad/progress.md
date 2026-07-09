# Story 1: Auto-generate: доклад — Progress

## Priority for Sprint 1 (decided 2026-07-07 — see .memory-bank/tasks/sprint-plan.md)

67 scenarios / 424 steps is far more than fits before Friday's deploy deadline. Work
these **P0** scenarios first, in this order — they're the walking skeleton that makes
the product actually work end-to-end and unblocks frontend integration. Branch:
`features/story-1-auto-generate-doklad`, PR into `dev` once P0 is green and deployed.

- [x] **P0-1** — Backend 1.1: Reject request with missing topic (all steps done through `green-acceptance`, see `decisions/request-validation-architecture-decision.md`)
- [x] **P0-2** — Backend 1.2: Reject request with out-of-range volume
- [ ] **P0-3** — Backend 2.1: Valid request is accepted and queued without waiting on the LLM call
- [ ] **P0-4** — Backend 4.1: A pending generation reports its status without document content
- [ ] **P0-5** — Backend 4.2: A completed generation includes the document content
- [ ] **P0-6** — Integration 1.1: A successful provider call produces a completed document
- [ ] **P0-7** — Integration 1.2: The requested volume converts to a pinned, tested prompt budget for Cyrillic text

**Everything else below (60 scenarios) is explicitly deferred past this Friday** —
retry policy, reconciliation sweep, load, most security/infra hardening. Do not work
them before P0-1..7 are green and deployed, no matter what order `/continue` would
otherwise pick.

**Ceremony cut for P0-1..7 only (decided 2026-07-09) — forced measure, sprint deadline
pressure, NOT a permanent process change:** after scenario 1.2's green-usecase work
unit took ~10 background agent dispatches for one step, we're dropping process weight
that doesn't gate correctness, to fit the remaining P0 scenarios before Friday:
- **Skip** the two pre-commit review passes (`agent-review-agent` + `premortem-agent`) —
  they're non-gating/advisory only, findings are a nice-to-have, not required for P0.
- **Skip** the full `/refactor` detector fan-out (3 concurrent cluster agents) — only
  refactor inline if a duplication/smell is obvious on sight; don't dispatch the fan-out
  for small diffs.
- **Do NOT skip**: red/green TDD cycle, `/test-review` (assertion strictness),
  `/test-coverage`. These are the actual correctness signal — cutting them would mean
  shipping P0 to prod unverified, which is worse than missing ceremony.
Revert this once P0-1..7 are green and deployed — resume full `/continue` ceremony
(review passes + refactor fan-out) for everything after.

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1: Reject request with missing topic
- [x] red-acceptance
- [x] design
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (rest) — Check 1 (ports): [S] no outbound port, rejects before persistence. Check 2 (exceptions): rest — ValidationException unmapped, no FastAPI app/exception handler exists yet. Check 3 (response shape): rest — placeholder http.server returns 501 instead of 400 `{"detail": "topic is required"}`. Checks 2+3 collapse into one rest pair. green-adapter rest must also introduce a minimal `RequestGeneration` usecase wrapping `Generation.create()` (controller must delegate to a usecase per coding-rules.md, none exists yet).
- [x] red-adapter rest
- [x] green-adapter rest
- [x] green-acceptance

### Scenario 1.2: Reject request with out-of-range volume
- [x] red-acceptance
- [x] design
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery — Check 1 (ports): [S] no outbound port, same as 1.1. Check 2 (exceptions): [S] `ValidationException` already mapped to 400 by the generic handler registered in 1.1's `green-adapter rest`. Check 3 (response shape): [S] router already forwards `volume_pages` through to `Generation.create`; response shape (400 + `{"detail": ...}`) matches acceptance expectation, same code path as 1.1. No adapter changes needed — only the acceptance test's skip marker (stale per agent-review finding) blocks green-acceptance.
- [x] green-acceptance — un-skipped only (no production code needed, adapter already sufficient per discovery above); 3/3 acceptance tests passed

### Scenario 1.3: Reject requirements/extra_wishes exceeding the length limit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4: Reject unsupported document type
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5: Ignore server-owned fields in the request body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6: Ignore a client-supplied creation timestamp
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.7: Accept and reject requirements/extra_wishes length limits for Cyrillic text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call
- [x] red-acceptance
- [x] design — see `decisions/persist-and-enqueue-architecture-decision.md`
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: An entirely Cyrillic request round-trips without corruption
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Replaying the same idempotency key does not create a duplicate generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A redelivered background job does not reprocess an already-progressing generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: A pending generation reports its status without document content
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: A completed generation includes the document content
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: Requesting a non-existent generation reports not found
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: A permanent generation-provider error fails fast without exhausting retries
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A transient generation-provider error is retried and can still succeed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Exhausting the retry budget fails the generation, never leaves it stuck
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: A generation abandoned by a dead worker is eventually reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: A generation still within its normal processing window is not prematurely reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6: A worker's genuine completion is never clobbered by a concurrent reconciliation sweep
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: Listing returns generations across all callers, most recent page first
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2: Paginating with a cursor is stable while new generations are being created
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.3: The list caps its page size even when far more generations exist
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.4: Generations with the same creation timestamp still list in a stable order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1: A successful provider call produces a completed document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: The requested volume converts to a pinned, tested prompt budget for Cyrillic text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Permanent and transient provider errors are handled differently
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A malformed or empty provider response is treated as a failure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: Each failure family is recorded with a distinguishable category server-side
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A hung provider call is cancelled at the job deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Redelivering the same background job does not call the provider twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: Redelivering a job for an already-failed generation does not reprocess it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: The document and the completed status commit together, never one without the other
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A commit failure after a successful provider call does not trigger a duplicate call
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: The bounded retry sequence fits within the job's overall deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1: A permanently failing generation does not block other generations from completing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1: Concurrent retries after a shared transient outage do not all retry at the same instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Frontend Scenarios (02_UI_Tests.md)

> Re-bootstrapped 2026-07-08: this section previously reflected the pre-rewrite
> "form is the entry point" flow. `01_AutoGenerateDoklad.md` and `02_UI_Tests.md` were
> revised 2026-07-07 for the Landing → type-modal → mode-modal → generation-form → chat
> flow; this section is now remapped to match that spec 1:1 (18 scenarios across 10
> sections, up from 11). No frontend code existed yet, so nothing here was in-flight.

### Scenario 1.1: The landing page displays the hero and primary CTA
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api — purely presentational (static hero heading + CTA button), no backend call; `POST /generations`/`GET /generations` belong to later scenarios in the flow. Handled entirely in the component (align-design).
- [S] green-frontend-api — see red-frontend-api skip reason
- [x] align-design
- [~] green-selenium
- [ ] demo

### Scenario 1.2: The primary CTA opens the document-type modal
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.1: The type modal shows all four document types, only доклад available
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.2: Selecting доклад opens the mode modal
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.1: The mode modal shows both modes, only Автоматический available
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.2: Selecting Автоматический режим opens the generation form
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: The generation form displays the input fields for the chosen type
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: The submit button is disabled until required fields are filled
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: Submitting the form shows a loading state and transitions to the chat/progress view
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.2: Activating submit twice before a response arrives only creates one generation
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 7.1: An empty topic shows an inline error before submission reaches the server
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 7.2: An out-of-range volume shows an inline error
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 8.1: A pending/in-progress generation shows a loading indicator, not real streaming
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 8.2: A completed generation displays the document content
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 8.3: A failed generation displays an error state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 9.1: "Create a new report" navigates back to the generation form
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 9.2: "Create a new request" from the failed state navigates back to the generation form
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 10.1: Navigating away with unfilled-but-entered form data warns before discarding it
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1: Injection payloads in free-text fields are stored and returned safely
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Document content and echoed input are served as escaped text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Server-owned fields cannot be set by the client
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Oversized free-text fields are rejected before reaching the generation provider
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: Generation identifiers are not predictable across consecutive creations
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: A generation-provider failure never leaks credentials or raw upstream detail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1: A flood of submissions cannot drive unbounded concurrent provider calls
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1: A malformed idempotency key is rejected, not passed through
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.1: A request with deeply nested or oversized JSON is rejected before parsing cost balloons
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: Generation submission sustains the configured throughput baseline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: A burst of submissions does not exceed the worker concurrency ceiling
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Throughput recovers after a burst subsides
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1: Generation submission fails cleanly when the database is unavailable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Pending generations resume processing after the database recovers
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Generation fails gracefully when the generation provider is unreachable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: The application fails fast at boot when required generation-provider config is missing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: The reconciliation sweep does not double-process the same stale generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A generation whose job was silently never enqueued is still reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Resource usage returns to baseline after repeated failure and cancellation handling
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
