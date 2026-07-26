# Generate → edit — Notes & Considerations

Companion to `18_GenerateThenEdit.md`. Warnings, forced guards from the hazard scan, and
cross-story seams. `interview.md` holds the decisions; `../../decisions/
editable-generated-docs-scope.md` holds the 3-session scope lock.

## Warnings

### Functional
- The whole flow is blocked on the story-5 **block-schema** editor migration — the
  current `inline*` editor cannot hold multi-paragraph generated text. Frontend story-18
  work must not start until that lands.
- GigaChat output format is **unverified** (interview ACTION). The CI FakeProvider emits
  markdown; prod may emit plain text. The parser must degrade to plain-text safely, and a
  test must exercise a plain-text (non-markdown) fixture, not only the fake's markdown.

### UI/UX
- The generation poll has no first-class **failed / poll-error** UI distinct from the
  "Generating" spinner — a `failed` generation would otherwise spin forever.
- Auto-open into an editable doc creates unsaved-state exposure on refresh/navigation.

### Technical
- Markdown→HTML is CPU work on untrusted model text — pathological nesting can be
  super-linear (markdown ReDoS). Bound the **source** length before parsing.

## Forced guards (fold into test-spec — each must go red on its hazard)

**Encoding / limits (grp 1, 6)**
- Round-trip multibyte fixture (Cyrillic + emoji + combining accent) through
  `from-generation` → `GET`, assert byte-exact after NFC.
- Content limit pinned to **Unicode code points**; boundary test with a 2-code-point
  grapheme straddling the limit → clean 4xx, never mid-grapheme truncation.
- Bound the **source** generation content before the parser runs (not only HTML output).
- Pathological/deeply-nested markdown completes within a wall-clock bound (no hang).

**Idempotency / concurrency / atomicity (grp 2, 3, 8) — the load-bearing seam**
- **Single guard closes all three:** a DB **unique constraint on `generation_id`**. Test:
  two concurrent `from-generation` for one `generation_id` (barrier at check→insert,
  ideally across instances) → exactly one `Document`, second returns the existing id.
- Rollback test: fail mid-conversion → zero orphan `Document`, zero orphan idempotency
  marker (dedup identity lives in shared storage, not in-memory).
- Client single-fire: two `completed` poll observations before the first `POST` returns →
  exactly one `POST` issued; out-of-order polls bind to latest.
- Read-after-write: editor opens from the `POST` response body; no re-read that could hit
  a lagging instance/replica.

**State / schema (grp 4)**
- Completed-only gate: transition matrix `completed→201`, `{pending,in_progress,failed}→
  409`, unknown status → fail closed.
- Rolling-deploy: old story-5 code inserts + reads `Document` against the new nullable
  `generation_id` column without error.
- Existing `GET /documents` consumer tolerates the new `generation_id`/`title` fields.
- On-delete policy for `generation_id` defined; deleting a parent leaves no dangling ref.

**Request boundary (grp 5)**
- Mass assignment: per-field test — body with `title`/`id`/`status`/`version`/spoof
  `generation_id` → persisted result unchanged; manual `POST /documents` rejects a
  client-supplied `generation_id`.
- URL-scheme sinks: markdown with `[x](javascript:...)`, `data:` link, `onerror` image →
  `href`/`src` stripped, not just `<script>`.
- Fail-closed: sanitizer/parser throws → 4xx/5xx, no `Document`, nothing unsanitized.

**Operability / disclosure (grp 7)**
- Conversion failure after `completed` emits a signal keyed by `generation_id`; happy path
  does not.
- Plain-text degrade branch emits a distinguishable signal (metric/log), distinct from
  the markdown path.
- Pin conversion against production GigaChat-shaped output, not only the FakeProvider.
- Sentinel disclosure: seed an internal value (DB text / id shape / stack frame), trigger
  each failure family (incl. new parser-failure), assert absent from body AND logs.

## Cross-story seams (reconcile before/at test-spec)

1. **Idempotency ↔ concurrency ↔ client double-fire** → one guard: unique constraint on
   `generation_id`. Confirmed load-bearing; client lock is a wasted-POST optimization.
2. **Stuck generation (never terminal)** → story 1 owns a poll/generation deadline; story
   18 needs a client-side conversion/poll deadline so it doesn't hang.
3. **IDOR on the created `Document`** (`GET`/`PUT /documents/{id}`) → story-5 ownership
   guard must be re-asserted to cover generated docs.
4. **Connection release on the insert** → reuses story-5 `SaveDocument` repository path.
5. **`GET /documents` pagination stability** → story-5 owned.
6. **Unsaved editor state** → may live in story-5 editor spec; story 18 introduces the
   auto-open path, so it must confirm the guard exists.
7. **Poll thundering herd / jitter** → story-1 `useGeneration` owns the poll; confirm it
   carries jitter/cap.

## Security Considerations
- Stored-XSS via model output is the primary risk — allowlist sanitize incl. URL schemes.
- IDOR: owner-scope every by-id op; 404 (not 403) for foreign/absent, indistinguishable.
- Mass assignment on the conversion body (server-owned fields).

## Integration Notes
- Reuses story-1 async generation + poll unchanged; story-5 `Document`/save/sanitize.
- New markdown-parser dependency must pass the CI `audit` (pip-audit) gate.

## Hazard-scan record
Scanned twice against catalogue **Groups 1–8** (full set at scan time):
- Story-level (2026-07-25) — gaps folded into `18_GenerateThenEdit.md` ACs / Core
  Requirements and this Notes file.
- Test-level (2026-07-26) — verified each guard is encoded as a scenario. Additional
  scenarios folded into the test files: full non-terminal state matrix (pending/failed),
  barrier-pinned concurrent conversion, stale-save version conflict on the generated doc,
  pathological-markdown wall-clock bound, editor-populated-from-response (no re-read),
  transient poll-error + never-terminal client deadline, markdown path emits no degrade
  signal, byte-identical 404 for the generated doc, sentinel redaction-to-token.
Re-scan required if a Group 9+ is added while this spec is still open.
