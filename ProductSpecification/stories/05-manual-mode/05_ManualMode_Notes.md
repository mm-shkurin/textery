# Manual input mode - Notes & Considerations

## Warnings

### Functional Warnings

- Don't let manual-create silently create a `Generation` shell "for consistency" —
  interview.md is explicit this path bypasses `Generation` entirely. A stray
  `Generation` row would break story #1's polling/list invariants (`GET /generations`
  is unscoped and would start returning empty-shell rows).
- Preset/template content (placeholder headings) is explicitly deferred — the empty
  document must not silently gain default headings as a "nice UX touch".
- Edit-after-save (reopening and continuing to edit) is in scope per the flow above,
  but full history/versioning of manual edits is not — that's story #12 (History).

### UI/UX Warnings

- Mode-select modal must not regress story #1's Автоматический card — this story only
  flips Ручной from "скоро" to active.
- Toolbar active-state (e.g. Bold highlighted when cursor inside bold text) is easy to
  skip and easy to get subtly wrong (off-by-one at format boundaries) — call out in
  test-spec.
- Empty state must not look broken/loading — distinguish "empty and ready to type" from
  a loading skeleton.

### Technical Warnings

- Editor formatting output must be sanitized before persist AND before render — sanitize
  once at the wrong layer (e.g. only client-side) and stored XSS is possible via a
  crafted `PUT /documents/{id}` body bypassing the editor UI.
- Reusing the `Document` model from story #1 means the save endpoint must not assume a
  completed `Generation` exists upstream (story #1's `Document` creation always follows a
  `Generation`; this path never does) — check for hidden foreign-key/not-null coupling
  before reuse.
- `content` max-size bound is "shared with story #1's limits" per spec but story #1 spec
  doesn't itself pin one explicitly for `Document.content` (only request fields like
  topic/requirements) — confirm/derive the actual bound during design-preview, don't
  assume unbounded.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- Preset/template structure (deferred, see interview.md) — good candidate for a fast
  follow once story 5 ships.
- Autosave, export, tables, advanced styles — story #10 (Text Editor polish), already
  tracked.

### UI/UX Suggestions

- Consider a subtle "unsaved changes" indicator distinct from the "Сохранено" confirmation,
  once autosave (story #10) isn't yet in place and users might navigate away mid-edit.

### Technical Suggestions

- When story #10 adds autosave, the explicit `PUT /documents/{id}` save endpoint built
  here should be reusable as-is (debounced autosave calling the same endpoint), not
  replaced.

---

## Technical Notes

### Load Considerations

- Per `ExpectedLoad.md`: multi-tenant, hundreds of concurrent users. Unlike story #1,
  this flow has **no async/LLM step** — creation and save are both synchronous,
  low-latency operations. No queue/worker involvement, so story #1's queue-depth
  concerns don't apply here; the load risk is plain request-rate on two simple
  endpoints (`POST /documents`, `PUT /documents/{id}`).
- No pagination concern introduced by this story (no new listing endpoint).

### Security Considerations

- Stored XSS: sanitize editor content server-side on save, not just client-side on
  render (OWASP A03: Injection).
- Anonymous, unauth'd `PUT /documents/{id}` means any client can overwrite any document
  by guessing/enumerating `document_id` — mitigated only by UUID non-guessability until
  story #7 auth lands; this is an accepted, temporary posture matching story #1's own
  `Generation` model (same interview.md note: "Auth/user_id — story 5 anonymous,
  dependency on story #7 not blocking").
- No server-owned-field mass-assignment: `PUT /documents/{id}` body must bind only
  `content` (and not `document_type`, `id`, `status`) — mirrors story #1's
  `POST /generations` DTO-binding requirement.

### Infrastructure Notes

- No new infrastructure — reuses existing API/DB stack from story #1.

### Integration Notes

- No external API dependency (this is the point of the story — no LLM call). No OAuth,
  no rate limits, no third-party integration risk.

---

## Additional Context

See `interview.md` for full scope discussion, explicitly-deferred items (preset
templates, AI+manual merge direction), and the DECISION log. Cross-references story #1
(`Document`/`document_type` reuse, mode-select modal) and story #10 (advanced editor
polish, autosave).

---

## Hazard-Catalogue Scan (8 groups, all dispatched)

Scanned against `.claude/guidelines/hazard-catalogue/_index.md` groups 1-8, 2026-07-14.
Every GAP below is folded into the main spec's Acceptance Criteria/Validation
Rules/Core Requirements (see those sections for the resulting testable requirement).

| Group | Verdict | GAPs folded |
|-------|---------|-------------|
| 1. Money/numbers/representation | GAPS | content-length truncation boundary (grapheme-safe reject); multibyte round-trip fixture requirement |
| 2. Re-run safety/ordering/atomicity | GAPS | `POST /documents` idempotency key (dup-submit protection); no-stray-`Generation` atomicity assertion |
| 3. Concurrency/consistency/distribution | GAPS | optimistic-concurrency (409) on `PUT` — lost-update guard |
| 4. Data lifecycle & schema | GAPS | manual `Document` status scope pinned (`draft` only, no gating); nullable `generation_id` compat with story #1 reads |
| 5. Request boundary & input | GAPS | IDOR named as accepted posture (not silently dismissed); concrete injection test (raw `<script>` via crafted `PUT`); mass-assignment per-field enumeration (`document_type`/`id`/`status`) |
| 6. Scale & resource limits | GAPS | pinned `content` max length (200,000 chars) — story #1 never pinned one, so this story owns it |
| 7. Time/operability/disclosure | GAPS | sanitize-divergence visibility (response reflects sanitized, not raw); error-body disclosure (404/422/409 generic shape); config-drift resolved by pinning the length here |
| 8. Client/frontend | GAPS | save-button in-flight lock + out-of-order response resolution; unsaved-edit-loss named as accepted posture (not silent) |

**Seams reconciled (cross-group, single guard each):**
- **Content max-length** fired independently in groups 1, 6, and 7 (truncation safety,
  unbounded-size, config-drift) — all three point at the same missing pin. Resolved once:
  200,000 chars, reject at boundary, in Validation Rules — not three separate guards.
- **Injection/sanitization** fired in groups 1 (seam only), 5, 7, and 8 — all converge on
  one concrete forced guard: crafted raw-HTML `PUT` body, assert neutralized at persist
  AND at render. One test covers all four groups' flags.
- **Idempotency (group 2, inbound POST) vs. lost-update (group 3, concurrent PUT)** are
  distinct properties, not one discharging the other: idempotency guards *repeated
  identical* submissions; optimistic-concurrency guards *concurrent different* edits.
  Both are now separate Acceptance Criteria.
- **IDOR (group 5) vs. destructive-overwrite-by-guessing (group 4 seam)** — both point at
  the same accepted, temporary anonymous-access posture already established by story #1's
  `Generation` model. Resolved as one explicit "accepted, temporary posture" statement in
  Core Requirements, not a blocking gap — consistent with interview.md's own DECISION that
  story #5 stays anonymous pending story #7.
- **Save in-flight lock (group 8) and no named "in-flight" screen state (group 8
  self-seam)** — one Core Requirement now covers both: client-side lock + out-of-order
  resolution implies the in-flight UI state exists.

No group was dismissed as a block; groups without gaps (destructive ops in group 4;
time/expiry in group 7; work-amplification/backpressure/retry-storm/pagination in group
6; compute-then-commit/external-call/timeout in group 2; async-delivery in group 3;
absent-vs-null and default-branch in group 5) were dismissed per-class with a reason
inline in each scan pass, not silently skipped.

---

## Hazard-Catalogue Scan — Test-Spec Level (8 groups, all dispatched, 2026-07-14)

Re-scanned after `/test-spec` drafted the 6 test files + extended variants — this pass
checks whether a *scenario* exists that would actually go red on each hazard, not just
whether the spec names the requirement. Every GAP is folded into the matching test file
as a critical-path scenario (never extended), per test-spec-format.md's rule.

| Group | Verdict | GAPs folded |
|-------|---------|-------------|
| 1. Money/numbers/representation | GAPS | version-field validation (negative/non-integer); boundary×multibyte-grapheme intersection; astral-plane (surrogate-pair) round-trip; NFC/NFD normalization-equality on duplicate-save detection |
| 2. Re-run safety/ordering/atomicity | GAPS | no-orphan-`Generation`-row assertion on a *failed* manual-document creation (previously only asserted on the happy path) |
| 3. Concurrency/consistency/distribution | GAPS | deterministic same-instant interleave / atomic-CAS test for `PUT` — distinct from the already-covered sequential lost-update scenario |
| 4. Data lifecycle & schema | GAPS | cross-story write-isolation: story #1's generation-completion path must never mutate a manual document's status |
| 5. Request boundary & input | CLEAR | none — IDOR correctly left untested as an explicitly-accepted, story #7-deferred posture (seam flagged for story #7's own test-spec to close later) |
| 6. Scale & resource limits | GAPS | concurrent-client retry-storm scenario after shared DB recovery; oversized-payload boundary tightened to accept-at-limit/reject-one-past (previously a vague "far larger than legitimate") |
| 7. Time/operability/disclosure | GAPS | fail-fast-on-missing-DB-config startup scenario; DB-unavailable 5xx body held to the same generic-error-shape guard as 404/422/409 |
| 8. Client/frontend | GAPS (1 fixed as inconsistency) | drafted `extended/02_UI_Tests_Extended.md` unsaved-nav-warning scenario contradicted the spec's own "accepted, no guard, deferred to story #10" posture — replaced with an explicit dismissal note instead of a scenario that would either fail by design or silently reverse a documented decision |

**Seams reconciled:**
- Group 8's finding was a genuine **artifact inconsistency**, not a missing scenario:
  the drafted extended UI test asserted a confirm-guard the spec explicitly declined to
  build. Resolved by dismissing the test, not by building the guard — the spec's
  posture is the source of truth here, and story #10 owns that protection.
- Group 3's gap is intentionally kept separate from the already-covered group 3
  "lost update" scenario (01_API_Tests.md §6.3): lost-update tests two *sequential*
  saves separated by a request round-trip; the new gap tests a *same-instant*
  interleave — same group, two different classes, not one discharging the other.
- Group 4's cross-story gap was folded into `extended/` (not critical-path) because it
  exercises story #1's own code path, which may not exist yet at this story's
  implementation time — flagged for whichever story lands second to pick up.

No group was dismissed as a block.
