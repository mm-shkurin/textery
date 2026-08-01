# Hazard Catalogue Scan — Story 4 test spec

Scanned 2026-08-01 against groups **1–8** — the full `_index.md` **Groups** list at that
date. A group added later makes this record a strict subset of the current list, and the
spec stale until re-scanned (see `_index.md`, "A new group obligates a re-scan").

| Group | Verdict | Disposition |
|-------|---------|-------------|
| 1 Money, numbers & representation | Money and numeric edges out of altitude — no arithmetic beyond story 1's pinned page budget. Text/encoding **fired** | Folded → `extended/01` 1.1 (byte-exact multibyte round-trip), `extended/01` 2.1 (case/whitespace type boundary under NFC) |
| 2 Re-run safety, ordering & atomicity | Idempotency **fired** (a generation is an external call that can be re-triggered). Compute-then-commit, transaction boundary: dismissed — prompt building is pure and persists nothing | Folded → `01` 3.4 (duplicate submit, provider called once), `extended/06` 1.1 (job redelivery), `extended/06` 1.2 (stale sweep). External-call failure modes → `06` 2.1–2.3 |
| 3 Concurrency, consistency & distribution | Races, lost update, read-after-write: dismissed as a block — nothing is read-modify-written by this story. Async delivery **fired** weakly via redelivery | Folded → `extended/06` 1.1, which is the same guard as the idempotency seam below |
| 4 Data lifecycle & schema | Dismissed as a block — no migration, no schema change, no new status transition. (Story 3 fires this group; story 4 does not) | — |
| 5 Request boundary & input | Output-context encoding **fired** (the prompt is a sink). Default-branch / fail-open **fired** (unknown type). IDOR, mass assignment, absent-vs-null: mostly dismissed — the request contract is untouched; absent-vs-null retained one case | Folded → `05` 1.1 and 1.2 (injection via all three user fields), `01` 1.4 (exhaustive over supported types, no catch-all), `01` 3.3 (unsupported type rejected), `extended/01` 1.3 (empty optional leaves no dangling label) |
| 6 Scale & resource limits | Unbounded size **fired** weakly — the template adds fixed overhead on top of story 1's field caps. Amplification, exhaustion, retry storms, pagination: dismissed, unchanged from story 1 | Folded → `extended/01` 1.2 (max-length request stays within the documented bound) |
| 7 Time, operability & disclosure | Time/expiry and config drift dismissed — no clock, no new env var. Partial-failure visibility and secret/PII disclosure **fired** | Folded → `05` 2.1 (prompt not logged verbatim), `05` 2.2 (provider body not echoed), `06` 2.3 (failure category recorded server-side) |
| 8 Client / frontend | Client-as-untrusted **fired**; non-happy-path UI **fired** | Folded → `05` 3.1 (a disabled card is not an authorization boundary — asserts acceptance deliberately), `02` 3.2 (failure state named per type), `02` 1.2 (other cards stay disabled) |

## Seams

- **Exhaustiveness (group 5, default-branch) × external-call failure (group 2).** One
  hazard, two framings: a document type with no template. A single guard owns it —
  `01` 1.4, parametrized over `SUPPORTED_DOCUMENT_TYPES`. It goes red when a fifth type
  is added without a template, in the domain, before a worker ever sees it. Without it
  the failure appears only at run time: after enqueue, burning the retry budget, ending
  as `failed` with nothing the client can act on.
- **Prompt injection (group 5, output encoding) × text handling (group 1).** One guard
  per direction: `05` 1.1 and 1.2 assert the structural instructions survive hostile user
  text in all three fields; `extended/05` 1.2 asserts the delimiter itself cannot be used
  to break out. `extended/05` 1.1 closes the far end — model output rendered as escaped
  text.
- **Idempotency (group 2) × async delivery (group 3).** Both point at the same setup with
  different assertions. `01` 3.4 owns the inbound duplicate request; `extended/06` 1.1
  owns the redelivered job. Neither is left to the other.

No unresolved GAPs.
