# Auto-generate: доклад — Notes & Considerations

## Warnings

### Functional Warnings

- The "list all generations" endpoint is a temporary stand-in for history, not the real
  feature (#12) — it has no per-user scoping because there is no user concept yet.
  Revisit at story #7/#12.
- If the OpenRouter model choice changes after this story ships, the prompt's token
  budget (derived from `volume_pages`) may need re-tuning for the new model's output
  characteristics.

### UI/UX Warnings

- Polling interval/backoff strategy is a frontend-phase concern, not covered here — flag
  for the frontend scenarios of this story.
- No estimated-completion-time feedback to the user during `pending`/`in_progress` —
  acceptable for story 1, revisit if it hurts perceived quality.

### Technical Warnings

- `arq` job timeout (300s default from the tech profile) must be re-tuned once the real
  OpenRouter model is picked — some models are much slower than others.
- No dead-letter/replay mechanism for permanently `failed` generations — acceptable for
  story 1 (no manual-retry UI in scope), but note it for a future support-tooling story.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- Show an estimated completion time based on `volume_pages`.

### UI/UX Suggestions

- Replace polling with WebSocket/SSE push once the frontend phase for this story lands.

### Technical Suggestions

- Consider structured logging of raw OpenRouter request/response (minus the API key) for
  debugging generation-quality issues later.

---

## Technical Notes

### Load Considerations

- Hundreds of concurrent users expected (`ExpectedLoad.md`) — the async `arq` design is
  the direct answer to this; worker concurrency and Postgres pool sizing get tuned during
  the load-test scenarios, not this story.

### Security Considerations

- No auth yet — `POST /generations` is fully public. This is a deliberate, tracked
  tradeoff (`known-debt.md` #2), not an oversight, but it means **no rate limiting or
  per-caller quota exists in this story** — anyone can spend the OpenRouter budget.
  Hazard-scan flagged this; the forced guards that DO exist now (idempotency-key
  enforcement, requirements/extra_wishes length cap, `arq` `max_jobs` ceiling) bound
  accidental duplication and per-request/worker-side cost, but **deliberate abuse/
  flooding protection (rate limiting, per-caller quota) is still out of scope** until
  story #7/#8 introduce identity and quotas.
- `GET /generations` (unscoped, lists everyone's generations) is a deliberate, temporary
  stand-in for history (see Functional Warnings above) — it also means every caller's raw
  `topic`/`requirements`/`extra_wishes` and generated content is world-readable. This is
  acceptable for a competition-demo/anonymous-only story, but is now tracked as
  `known-debt.md` #4: **must be removed or gated before any real user identity/PII could
  ever flow through this table** (i.e., no later than story #7).
- User-supplied `topic`/`requirements`/`extra_wishes` are interpolated into the LLM
  prompt. No injection risk in the traditional sense (the LLM's output is never
  executed/evaluated), but store the raw input for auditability.
- Document content and echoed user input must be served as escaped text (Core
  Requirements) — this is an output-encoding/XSS guard for whenever a frontend renders
  it, not a prompt-injection guard.
- `OPENROUTER_API_KEY` and raw OpenRouter error bodies must never leak into a response or
  log (Core Requirements) — verified with a sentinel-value test, not just a code-review
  assumption.

### Infrastructure Notes

- `OPENROUTER_API_KEY` lives in `backend/.env` (local only, no cloud secret store yet —
  existing project decision).
- The `arq` worker is a separate process/container from the API (see
  `infra/architecture.md`).

### Integration Notes

- See `interview.md` for the OpenRouter API documentation link, auth requirements, and
  the decision to switch away from the originally-planned direct Anthropic API.
- The specific OpenRouter model string for story 1 is an open config decision
  (`OPENROUTER_MODEL` env var) — does not block implementation.

---

## Hazard Catalogue Scan (2026-07-06)

Scanned against all 8 groups in `.claude/guidelines/hazard-catalogue/_index.md` at scan
time. Every GAP was folded into Core Requirements/Validation Rules above (see the main
spec file); this section records the classes that were dismissed and the cross-group
seam reconciliation, so the reasoning isn't lost.

### Dismissed (trigger did not fire)

- **Group 1** — no currency/percentage/financial rounding in this story (billing is #8).
- **Group 2** — compute-then-commit (batch/multi-item sequencing): only one compute step
  (one OpenRouter call) and one commit step per job; no loop of independent side effects.
- **Group 3** — lost update / stale overwrite: no user-facing load→edit→save flow exists
  yet (read-only client, single async writer); the worker's own status-write race is
  covered under the seam-synthesized guard below, not this class.
- **Group 4** — destructive/data-loss ops: no delete/update/bulk-mutate endpoint exists
  anywhere in this story's scope.
- **Group 5** — absent-vs-null-vs-default: no PATCH/partial-update surface exists
  (create-only endpoint); the acute "omit means keep existing" hazard doesn't apply.
- **Group 5** — authorization/IDOR: dismissed as a *current-story* gap, not because it's
  irrelevant, but because `GET /generations` already grants the same unscoped visibility
  by deliberate design — a by-id lookup adds no incremental disclosure. See the
  `generation_id`-opacity seam below for the forward-looking mitigation, and
  `known-debt.md` #4 for the tracked follow-up.
- **Group 6** — work amplification (N+1/fan-out): single bounded OpenRouter call per job,
  no batch endpoint, no per-element fan-out.
- **Group 8** — client-as-untrusted/unsaved-state: this pass covers the backend API
  contract only; the actual frontend (and its UI-state/unsaved-data hazards) is a later
  scenario phase for this story, not silently skipped.

### Cross-group seams (reconciled)

1. **Idempotency (G2) × async delivery/concurrency (G3) × terminal-state correctness
   (G4).** Three passes each flagged a version of the same underlying risk: `arq`
   redelivery or two worker instances could double-process one `Generation`, and nothing
   stopped a write from landing on an already-terminal row. **Single guard**: status
   transitions are atomic conditional updates gated on expected prior status (see Core
   Requirements) — one mechanism closes all three flagged angles. Confirmed: the
   conditional-update guard is the one both G2 and G3's passes pointed at without either
   fully owning it; G4's transition-matrix concern is subsumed because a terminal-row
   write only succeeds if the `WHERE` clause matches a non-terminal expected status.
2. **`generation_id` opacity (G5 IDOR) × schema evolution (G4, story #7 retrofit).**
   Resolved by making the ID a UUID now (Core Requirements) — cheap today, and removes
   sequential-ID enumeration as an attack surface before story #7 adds real per-owner
   authorization.
3. **Unscoped `GET /generations` disclosure (G7) × request-boundary/IDOR (G5).** G7's
   pass flagged the list endpoint's disclosure but attributed the root cause to a missing
   authorization boundary (G5's territory); G5's own pass separately concluded IDOR
   doesn't fire *incrementally* here because the list endpoint already grants the same
   visibility. Reconciled as: no missing authorization guard is addable today (no
   principal exists to authorize against), so the resolution is tracking + a hard
   removal/gating deadline, not a code guard — recorded as `known-debt.md` #4.

### Full disposition tally

23 fired GAPs across 8 groups (including the idempotency-key AC gap from the re-run of
Group 8) → 3 seams collapsed 6 of them into 2 consolidated guards → 18 distinct Core
Requirements added, 1 tracked as new known-debt (`known-debt.md` #4), 8 classes
dismissed with reasons above.

---

## Test-Spec Hazard Catalogue Scan (2026-07-06)

A second, independent scan ran against the drafted `tests/*.md` files themselves (not
the story-spec prose) — the same 8 groups from `_index.md` at scan time, per the
`/test-spec` workflow's Phase 3. This scan is finer-grained than the story-spec scan:
it checks whether each Core Requirement above actually has an *executable Gherkin
scenario* that would fail on the hazard, not just a prose mention. It found 20 concrete
test-scenario gaps and 5 scenarios that existed but were misplaced in `extended/` when
they close a named Core Requirement or a real production risk (hazard-derived guards are
always critical-path, never "nice to have").

### New scenarios folded in (all main/critical files)

- `01_API_Tests.md`: §1.6 (created_at mass-assignment), §1.7 (Cyrillic length-limit
  boundary), §2.2 (Cyrillic round-trip, promoted from extended), §5.5 (not prematurely
  reconciled within the staleness window), §5.6 (worker-completion vs. sweep race),
  §6.3 (list page-size cap), §6.4 (pagination tiebreaker for equal timestamps). §4.1
  strengthened to assert the real POST→GET path, not a fixture insert.
- `02_UI_Tests.md`: §3.2 (double-submit collapses to one generation), §7.1 (unsaved-input
  navigate-away warning).
- `03_Load_Tests.md`: §3.1 (burst-recovery, promoted from extended).
- `04_Infrastructure_Tests.md`: §4.1 (boot-time config validation), §5.1 (sweep mutual
  exclusion across instances), §5.2 (sweep also catches a job that was never enqueued —
  closes the Group 2×Group 3 outbox/silent-drop seam), §5.3 (resource-handle count
  returns to baseline).
- `05_Security_Tests.md`: §3.1 extended to include `created_at`. §6.1 strengthened to
  assert captured-log redaction, not just response-body absence. §8.1 (CRLF header
  injection, promoted from extended), §9.1 (oversized/nested JSON, promoted from
  extended).
- `06_Integration_Tests.md`: §1.2 (Cyrillic pages→budget conversion pinned constant),
  §2.3 (distinguishable failure category persisted/logged), §4.2 (redelivery onto an
  already-`failed` row, mirroring §4.1's `completed` case), §5.1/§5.2 (transaction
  atomicity — Document+status commit together, no duplicate provider call after a lost
  commit), §6.1 (deadline-budget composition distinct from the single-hang case in §3.1),
  §7.1 (a permanently-failing generation doesn't block a valid one), §8.1 (retry-jitter
  spread, promoted from extended).

### Seam reconciliation (this scan)

- **G2×G3 outbox/silent-drop seam**: Group 3's pass flagged that the existing
  worker-death reconciliation (§5.4) assumes a job *was* leased before the worker died —
  it doesn't cover a job that was silently never enqueued at all. Resolved by extending
  the same sweep mechanism to cover both cases explicitly (`04_Infrastructure_Tests.md`
  §5.2), rather than building a separate transactional-outbox mechanism — one guard,
  two triggers.
- **G3×G4 terminal-state/race seam**: Group 3 (sweep-vs-worker race) and Group 4
  (terminal-state protection tested only for `completed`, not `failed`) both point at the
  same underlying atomic-CAS mechanism from different angles. Resolved as three distinct
  scenarios on the one mechanism, not three mechanisms: `01_API_Tests.md` §5.6 (worker vs.
  sweep), `06_Integration_Tests.md` §4.2 (redelivery vs. failed), `04_Infrastructure_Tests.md`
  §5.1 (sweep vs. sweep).
- **G2×G8 client-side idempotency seam**: Group 8 flagged that the server-side
  idempotency-key guard (`01_API_Tests.md` §3.1) has no client-side counterpart proving
  the UI actually reuses one key across a double-click. Resolved by `02_UI_Tests.md` §3.2,
  with its DSL reference tying the double-click to the same `Idempotency-Key` mechanism.

### Dismissed (test-spec scan only; see story-spec scan above for the first-pass dismissals)

- Numeric edges & precision (Group 1, class 2) — no arithmetic surface beyond the
  pages→budget conversion already covered under class 1.
- Compute-then-commit ordering (Group 2) — one compute step, one commit step per job, no
  batch/loop shape.
- Lost update / stale overwrite (Group 3) — no load→edit→save flow exists in this story.
- Destructive/data-loss operations (Group 4) — no delete/update endpoint exists.
- Absent-vs-null-vs-default (Group 5) — no PATCH/partial-update surface exists.
- Authorization/IDOR (Group 5) — no principal exists yet to authorize against; already
  tracked as `known-debt.md` #4.
- Async ordering-reversal (Group 3, sub-class) — only one event per generation, nothing
  to reverse.
- Client-as-untrusted mid-generation unsaved state (Group 8) — once submitted, there's no
  client-side state left to lose.

### Full disposition tally (this scan)

~30 findings across 8 groups → 3 seams reconciled → 20 new scenarios added, 5 scenarios
promoted from extended to main, 2 existing scenarios strengthened, 8 classes dismissed
with reasons above.

---

## Additional Context

- See `interview.md` for the full external API context, the OpenRouter decision
  rationale, and the testing-strategy decision (stub server in acceptance tests, never
  the real OpenRouter API).
