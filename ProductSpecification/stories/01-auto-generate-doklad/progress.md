# Story 1: Auto-generate: доклад — Progress

## Priority for Sprint 1 (decided 2026-07-07 — see .memory-bank/tasks/sprint-plan.md)

67 scenarios / 424 steps is far more than fits before Friday's deploy deadline. Work
these **P0** scenarios first, in this order — they're the walking skeleton that makes
the product actually work end-to-end and unblocks frontend integration. Branch:
`features/story-1-auto-generate-doklad`, PR into `dev` once P0 is green and deployed.

- [ ] **P0-1** — Backend 1.1: Reject request with missing topic (`red-acceptance` + `design` + `red-usecase` + `green-usecase` done, see `decisions/request-validation-architecture-decision.md`; `adapters-discovery` next)
- [ ] **P0-2** — Backend 1.2: Reject request with out-of-range volume
- [ ] **P0-3** — Backend 2.1: Valid request is accepted and queued without waiting on the LLM call
- [ ] **P0-4** — Backend 4.1: A pending generation reports its status without document content
- [ ] **P0-5** — Backend 4.2: A completed generation includes the document content
- [ ] **P0-6** — Integration 1.1: A successful provider call produces a completed document
- [ ] **P0-7** — Integration 1.2: The requested volume converts to a pinned, tested prompt budget for Cyrillic text

## Frontend framework-skip decision (decided 2026-07-09 — speed measure)

Sprint velocity is too slow for the deadline (1/74 scenarios after the full 8-step
frontend cycle on the landing hero alone). To compress: **Frontend Scenarios 1.2, 2.1,
2.2, 3.1, 3.2 (the CTA→modal trigger, the document-type modal, and the mode modal) are
built WITHOUT the TDD framework** — no red-selenium/red-frontend/green-frontend/
red-frontend-api/green-frontend-api/align-design/green-selenium/demo cycle. Write the
components directly as code, verify by eye in the browser once, mark all 8 checkboxes
`[S]` with this note as the reason. 1.2 was folded in after starting the modal work —
it is one line of glue (CTA onClick opens the type modal) with no logic of its own
separate from the modal it opens; testing the trigger in isolation from its
destination added no value.

**Why:** both modals are near-static UI (pick doc type, pick mode) with the framework's
per-scenario ceremony costing far more than the risk it buys here. The one piece of
real logic in this pair — "only one option enabled, rest disabled" (доклад-only,
Автоматический-only) — has no automated regression coverage after this decision; any
future change nearby must be re-verified by hand in the browser, not caught by a test
suite.

**Scope of the exception — do NOT extend it further without a new decision:**
Frontend Scenarios 4.1 onward (generation form → chat/progress/result flow, i.e. the
"chat") keep the full framework unchanged. That is where the real risk lives (field
validation, double-submit race in 6.2, three progress states, back-navigation) and
where a bug reaching demo actually costs the product working. If sprint pressure later
tempts skipping framework there too, that requires a fresh explicit decision, not a
silent extension of this one.

**Additional ceremony trim for 4.1 onward (still full framework, lighter steps):**
`demo` is skipped (`[S]`) for every remaining frontend scenario — visual-only, non-gating,
catches nothing green-selenium didn't already catch. `align-design` targets "matches the
mockup", not pixel-perfect — full design-review rigor stays only where visual precision
actually matters (already done for the landing hero).

**Layout deviation for 4.1 onward (decided 2026-07-09):** the standalone generation-form
page (mockup 04, spec section 4) is skipped entirely — see `.memory-bank/tasks/known-debt.md`
#8 for the full mapping and what it invalidates (scenario 7.2 in particular). Instead,
after the mode modal the visitor lands on a single doc-left/chat-right screen (mockups
05-07 layout, columns flipped: document wide on the left, chat panel narrow on the
right). The initial request is one free-text chat input (messenger-style), not four
discrete fields — mapped to `topic`; `volume_pages` sent as a fixed default (5);
`requirements`/`extra_wishes` sent empty. Read known-debt #8 before touching Scenarios
4.1-9.2 in a future session — the checkbox/scenario text below still describes the
original 4-field form and has not been rewritten.

**Logic/view split (decided 2026-07-09):** every component from Scenario 4.1 onward
splits into a presentational component (markup/CSS only, props in) and a `use*` hook
(state, validation, API calls, submit logic) that owns everything else. `align-design`
then only ever touches the presentational half — the hook, and any red/green-frontend
coverage of it, stays untouched when the design gets reskinned later. E.g. `useGenerationForm`
(state/validation/submit) + `GenerationForm` (renders from the hook's return value).

**Everything else below (60 scenarios) is explicitly deferred past this Friday** —
retry policy, reconciliation sweep, load, most security/infra hardening. Do not work
them before P0-1..7 are green and deployed, no matter what order `/continue` would
otherwise pick.

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
- [~] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Reject request with out-of-range volume
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

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
- [ ] red-acceptance
- [ ] design
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
- [x] green-selenium
- [x] demo

### Scenario 1.2: The primary CTA opens the document-type modal
- [S] red-selenium — framework-skip decision 2026-07-09 (speed measure, see note above)
- [S] red-frontend — see framework-skip decision
- [S] green-frontend — built directly, verified by eye in browser
- [S] red-frontend-api — no backend call, purely local UI state
- [S] green-frontend-api — see red-frontend-api skip reason
- [S] align-design — matched to mockup by eye, no formal align-design pass
- [S] green-selenium — see framework-skip decision
- [S] demo — see framework-skip decision

### Scenario 2.1: The type modal shows all four document types, only доклад available
- [S] red-selenium — framework-skip decision 2026-07-09 (speed measure, see note above)
- [S] red-frontend — see framework-skip decision
- [S] green-frontend — built directly, verified by eye in browser
- [S] red-frontend-api — no backend call, purely local UI state
- [S] green-frontend-api — see red-frontend-api skip reason
- [S] align-design — matched to mockup by eye, no formal align-design pass
- [S] green-selenium — see framework-skip decision
- [S] demo — see framework-skip decision

### Scenario 2.2: Selecting доклад opens the mode modal
- [S] red-selenium — framework-skip decision 2026-07-09 (speed measure, see note above)
- [S] red-frontend — see framework-skip decision
- [S] green-frontend — built directly, verified by eye in browser
- [S] red-frontend-api — no backend call, purely local UI state
- [S] green-frontend-api — see red-frontend-api skip reason
- [S] align-design — matched to mockup by eye, no formal align-design pass
- [S] green-selenium — see framework-skip decision
- [S] demo — see framework-skip decision

### Scenario 3.1: The mode modal shows both modes, only Автоматический available
- [S] red-selenium — framework-skip decision 2026-07-09 (speed measure, see note above)
- [S] red-frontend — see framework-skip decision
- [S] green-frontend — built directly, verified by eye in browser
- [S] red-frontend-api — no backend call, purely local UI state
- [S] green-frontend-api — see red-frontend-api skip reason
- [S] align-design — matched to mockup by eye, no formal align-design pass
- [S] green-selenium — see framework-skip decision
- [S] demo — see framework-skip decision

### Scenario 3.2: Selecting Автоматический режим opens the generation form
- [S] red-selenium — framework-skip decision 2026-07-09 (speed measure, see note above)
- [S] red-frontend — see framework-skip decision
- [S] green-frontend — built directly, verified by eye in browser
- [S] red-frontend-api — no backend call, purely local UI state
- [S] green-frontend-api — see red-frontend-api skip reason
- [S] align-design — matched to mockup by eye, no formal align-design pass
- [S] green-selenium — see framework-skip decision
- [S] demo — see framework-skip decision

### Scenario 4.1: The generation form displays the input fields for the chosen type
- [~] red-selenium
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
