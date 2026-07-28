# AI chat editing — Acceptance Criteria

Companion to `19_AiChatEditing.md` (split for the 200-line file limit). Every bullet is
a requirement a downstream test must be able to go red on.


### Request boundary & authorization

- `POST /ai-edits` on a caller-owned document returns 202 with an opaque `edit_id` (wire
  type UUID string) and `queued`; the document is not mutated at request time.
- Absent document, or one owned by another account → 404 (never 403), byte-identical body
  for absent vs foreign, on every one of the seven endpoints — including for `edit_id` and
  revision numbers, which must not leak existence.
- Cross-resource IDOR: an `edit_id` or revision `n` belonging to *another document of the
  same owner* → 404; the path document id is authoritative, never decorative.
- Expired / garbage / absent Bearer → one identical 401 body on all seven endpoints.
- Mass assignment: `POST /ai-edits` persists server-derived values for every server-owned
  field a body may carry (`status`, `edit_id`, `account_id`, `document_id`, `created_at`,
  `seq`, quota fields, `version`, `revision_number`), asserted per field; a body sent to
  `restore` is ignored entirely — content comes only from revision `n`, `source` is
  server-set to `restore`.
- Absent-vs-null-vs-default: `selection` omitted → whole-document edit; `selection: null`
  and `{start:null,end:null}` → 422 (shape), `{start:0,end:0}` → 400 (semantic), never a
  silent whole-document rewrite. `base_version` absent, `null` and `0` each → 422 before
  any row is written.
- Neither list endpoint takes an `order` parameter — ordering is fixed server-side. A
  malformed `limit`/cursor → 400, never interpolated; `limit` above the server cap is
  CLAMPED, not rejected, and never unbounded.
- A `message` containing `\r\n` plus a forged log prefix produces one structured log
  record, not two.

### Edit lifecycle & re-run safety

- One active edit per document: while an edit is non-terminal a second `POST` → 409, and
  `POST /revisions/{n}/restore` → 409; the guard is a DB uniqueness/CAS check so two
  concurrent instances cannot both win.
- Same `Idempotency-Key` replayed (sequentially or concurrently) returns the same
  `edit_id` with the edit's CURRENT status (a replay once the edit is `streaming` or
  terminal must stay representable), never a second edit and never a second chat message;
  a *different* key with identical body creates a new edit. The SAME key with a different
  body (message, selection or base_version) → 422 on the fingerprint mismatch, never a 202
  that silently discards the new instruction. Missing/blank key → 4xx before any row.
- **Worker-side (outbound) idempotency:** re-executing the job for the same `edit_id`
  produces exactly one paid provider call, one revision, one assistant message and one
  quota charge. An edit that applied its CAS but died before the terminal event must not,
  on requeue, apply a second revision or re-call the provider.
- A `DocumentEdit` is created in exactly `queued`; status cannot be set at construction
  from any input path.
- Terminal states (`done`, `error`, `cancelled`) are **absorbing**: cancel, worker-apply,
  chunk-append and reaper-requeue against a terminal edit are rejected with no mutation
  and no side effect. Illegal edges (`done → streaming`, `cancelled → done`) are rejected.
- Cancel and worker completion resolve through a single CAS on edit status to exactly one
  terminal state; an edit that reached `cancelled` never applies content, never writes a
  revision, never charges quota.
- **Late apply is impossible:** once an edit is terminal by cancel, client timeout or the
  reaper, an in-flight provider result cannot commit — no revision, no version bump, no
  assistant message, no quota charge after terminalization.
- A worker that dies mid-edit leaves the edit reclaimable by deadline (the
  `RequeueStaleGenerations` pattern), so a document is never permanently locked. Requeue
  is bounded by a maximum attempt count, after which the edit is driven terminal `error`
  and never requeued again; a healthy edit queued behind a poison edit still processes.
- A committed edit row whose enqueue was dropped is still eventually executed (the reaper
  covers never-started jobs, explicitly, not only dead workers); a job dequeued before its
  row is visible retries rather than failing permanently.
- The stale-edit reaper is mutually exclusive with itself via a DB-backed lease with
  expiry: a second activation started while the first runs does disjoint work.

### Atomicity, concurrency & consistency

- Compute-then-commit: the provider call happens outside the write transaction. The
  document CAS, the revision row, the assistant chat message and the terminal event row
  commit as **one** unit — force a failure on the last write and no revision exists
  without its message, no version bump without its revision.
- The terminal `done` event becomes visible to SSE readers only *after* that commit: a
  client issuing `GET /documents/{id}` and `GET /revisions` on receipt of `done` observes
  the `{version, revision_number}` the event carried — never an earlier version, never a
  revisions list missing that row.
- Chunk event rows written before a failed apply stay committed and replayable; the edit
  still emits exactly one terminal `error` after them — no tail without a terminator.
- Manual `PUT /documents/{id}` racing an AI edit on the same `base_version`: exactly one
  wins the CAS, the loser gets 409, no content is silently overwritten.
- A **worker** apply whose `base_version` no longer matches ends the edit terminal with a
  distinct `error` code, writes no revision and no partial content, and refunds quota.
- Restore performs the same single-statement CAS against the version it read (zero rows
  affected → 409), so two concurrent restores cannot collide on `version+1`.

### Streaming

- SSE emits `chunk` events with a strictly increasing per-edit `seq`, then exactly one
  terminal event — `done`, `error` or `cancelled`. That set equals the terminal values of
  `status`, so no terminal state exists that the stream cannot express; a cancel is never
  folded into `error`. `seq` is allocated per edit and never reused across worker
  attempts. Terminal state is also readable from `GET /ai-edits/{edit_id}`.
- Reconnect with `Last-Event-ID: <seq>` replays only events after `seq`, in order, with no
  gap and no duplicate — including after a requeue and after the edit already finished.
  Unknown/negative → from the start, never a crash; a large tail streams in bounded
  batches, never one unbounded materialization. The terminal event is the one exception:
  it is re-emitted unconditionally, so reconnecting with the `last_seq` read from
  `GET /ai-edits/{edit_id}` terminates instead of hanging silent.
- **SSE framing is injection-safe:** a chunk whose text contains `\n\ndata: …\n\nevent:
  done\n\n` or a bare `\r` is delivered as exactly one `chunk` event with the text intact —
  no forged terminal event, asserted on the raw wire bytes.
- Chunk boundaries fall on grapheme boundaries (or concatenation is byte-level before a
  single decode): a boundary mid-emoji or mid-combining-sequence yields no replacement
  character and a byte-exact final document.
- Errors arrive as `event: error` with a stable code, never a silent drop; the stream then
  closes. An edit with events but no terminal event resolves terminal via the reaper within
  the deadline — `GET /ai-edits/{edit_id}` never returns a non-terminal state older than it.
- Unknown constants (`event` type, edit `status`, revision `source`) follow a stated
  unknown-enum policy — preserved-unknown or clean reject — never silently coerced to the
  first constant, never a stream crash; the client treats an unrecognized terminal kind as
  `error` (unfreeze + retry), never as success.

### Content, units & sanitization

- Edit result over `DocumentContent`'s 200 000 **code-point** limit → terminal `error`, no
  partial save, never truncated mid-grapheme. Order is pinned: normalize to NFC, then
  measure, then apply offsets.
- Selection offsets are **code points** on the wire, tied to `base_version`; a document
  containing an astral character before the selection still rewrites exactly the selected
  range (UTF-16-index confusion goes red). Out-of-range/stale → clean 4xx.
- Selection-scoped edit rewrites only the selected range; the rest is byte-identical
  (after NFC).
- The context-fit threshold is measured in code points of `DocumentContent` (the spec
  states the token-per-code-point assumption it makes); boundary tests at threshold−1 /
  threshold / threshold+1 with multibyte content. Above it, a whole-document edit is
  rejected with a specific code and a selection is required.
- `message` max length is measured in code points; the limit is asserted with all-multibyte
  content.
- Model output passes the existing `HtmlSanitizer` allowlist before persist: `<script>`,
  event handlers and `javascript:`/`data:` sinks are neutralized in storage and in every
  render, including streamed chunks. Case-folding in the allowlist uses an invariant
  locale — `<SCRIPT>` / `JAVASCRIPT:` stay neutralized under a Turkish locale.

### Quota, revisions & history

- Daily per-account quota (env-configured) enforced by a DB counter: over-quota → 429 with
  a reset hint. The day boundary is one canonical zone, computed from an **injectable
  clock**; a clock pinned at 23:30 in a non-UTC zone buckets into the intended day.
- The counter is not consumable twice concurrently, never goes negative, and refund is
  idempotent per `edit_id` (cancel + reaper both terminalizing charges once, refunds once).
  Charge per accepted edit, refund on infrastructure failure and on CAS miss, not on model
  refusal. A quota-store read that errors or times out **denies** the request.
- Restore of revision `n` creates `version+1` with revision `n`'s content; history only
  grows, restore-of-a-restore works, unknown/foreign revision → 404, non-integer/overflow
  `n` → 404 (never 500). Restore is single-shot: a double-click creates exactly one new
  version.
- Revision origin is defined: the FIRST mutation of a document with no history writes two
  revisions in one transaction — revision 1 the pre-mutation content (`source: manual`),
  revision 2 the result — so the first AI edit is rollbackable. Before that first
  mutation, `GET /revisions` and `GET /messages` return a valid empty page.
- Both list endpoints are owner-scoped, keyset-paginated with a stable order under
  concurrent inserts, capped page size, constant query count per page (no N+1), and never
  return document content in the list view.
- Chat messages persist across sessions and survive an edit that produced no document
  change; the terminal event distinguishes "done, changed" from "done, unchanged".

### Operability, config & limits

- Error bodies for 4xx/5xx expose a stable generic shape; a seeded sentinel (DB text,
  prompt text, provider payload, stack frame, Bearer token, `Idempotency-Key`) is redacted
  to a fixed marker — asserted on the marker's presence, not on the raw string's absence —
  in responses, SSE events and logs.
- Stale-edit reclaim, quota refund, and cancel/timeout terminalization each emit an
  attributable signal (edit id + document id / account id); the happy path emits none.
- Provider failures are enumerated with a distinct terminal code and disposition each:
  connect timeout, read timeout, 4xx (no retry), 5xx (bounded retry), malformed/empty body,
  mid-stream truncation. Connect and read timeouts are finite and configured.
- Timer ordering is a startup-validated invariant: provider timeout × retries < edit
  deadline < `proxy_read_timeout`, and client timeout ≥ edit deadline. Units are pinned
  (seconds) at every hop. Behaviour is asserted at deadline−ε, at, and after.
- Retries and reconnects carry exponential backoff with jitter and an attempt cap: worker
  retries against a recovering provider, reaper requeue of a post-outage backlog (batch
  cap / stagger), client SSE reconnect, and cross-instance event polling are not
  synchronized on one tick.
- Concurrent stream connections and DB pool size have stated bounds and a defined
  behaviour at exhaustion (reject with a code, never a silent hang); after M clients abort
  mid-edit, open connections and checked-out DB connections return to baseline.
- `document_edit_events` has a stated retention/pruning bound, and every new table declares
  its `ON DELETE` policy (DB and ORM agreeing) so a deleted document or edit leaves zero
  orphans; the tail query is served by the `(edit_id, seq)` index.
- Config (context-fit threshold, daily quota, edit deadline, Redis URL) is env-driven and
  fails closed at startup — for both the web and the worker process — not per-request. A
  non-dev environment booting with the edit provider set to `fake` fails fast.
- New tables arrive by additive migration; a rolling deploy leaves story-5/18 document
  reads and writes working against the old code path, asserted as a guard.
- `proxy_buffering off` and `proxy_read_timeout` > edit deadline are declared in `infra/`
  and asserted by an infrastructure scenario (first chunk observed before the response
  completes), never hand-edited on a host.

See `19_AiChatEditing_Criteria_Client.md` for the client-side criteria.
