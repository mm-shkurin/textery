# Story 12 — Hazard Catalogue Scan Record

Scanned at test-spec, over all six category files plus `extended/`.

**Group set at scan time** (`.claude/guidelines/hazard-catalogue/_index.md` **Groups**):
1 Money/numbers/representation · 2 Re-run safety/ordering/atomicity ·
3 Concurrency/consistency/distribution · 4 Data lifecycle/schema ·
5 Request boundary/input · 6 Scale/resource limits · 7 Time/operability/disclosure ·
8 Client/frontend. A group added after this date makes this record stale — re-scan
while the spec is still being worked.

**Verdicts**: every group returned GAPS. No group was dead; every group's triggers fired.

## Dispositions

All 45 fired-trigger GAPs were folded as named scenarios. None was dismissed.

| Group | Folded into |
|-------|-------------|
| 1 | API 1.9 (threshold in declared unit), 4.7 (locale-independent case-fold), 5.4 (integer-type bound), 6.5 (multibyte round-trip), 8.10 (key comparison), 8.11 (ceiling accepted then refused), 10.8 (slot TTL both directions) |
| 2 | API 8.14 (orphan on last-write failure), 10.12 (caller abort cancels scan), Integration 1.6 (commit fails → no job), 1.7 (enqueue timeout), 2.4 (document written, status lost), 2.5 (partial sweep batch) |
| 3 | API 8.12 (concurrent retries at ceiling), 10.9 (slot claim race), Integration 1.8 (lost publish still delivered), 2.6 (disjoint sweep activations), 2.7 (poison job), 3.4 (duplicate delivery) |
| 4 | API 7.4 (unrecognized status), 8.13 (initial status), 9.4 (deprecated endpoints unchanged), Infra 2.4 (N-1 write path), Infra 4.1 (slot reclaim blast radius) |
| 5 | API 5.5 (omitted/empty/repeated), 6.6 (log injection), 9.3 (server-owned fields, replay rebinding), 1.10 (config fail-closed), UI 3.5 (reflected term inert), Security 8.1 (client-supplied preview) |
| 6 | API 2.7 (fixed query count), 3.7 (ties across a page boundary), 10.10 (resources return to baseline), 10.11 (backoff hint), UI 5.4 (no immediate re-arm), UI 7.6 (client dedupe) |
| 7 | API 1.9/1.11, 10.13 (correlation id in the log), 10.14 (degraded-path signals), UI 1.7 (local day), Infra 3.1/3.2 (config validation), Security 7.2 (log sentinels), 7.3 (sanctioned envelope) |
| 8 | UI 4.3 (latest sort wins), 7.5 (failed later page), 7.6 (dedupe on kind+id) |

## Seams reconciled (synthesis pass)

| Seam | Guard that carries it |
|------|----------------------|
| Key equality (1) ↔ inbound idempotency (2) | API 8.10 |
| Transaction boundary (2) ↔ async delivery (3) | Integration 1.6 (boundary) **and** 1.8 (delivery) — two guards, not one |
| Inbound idempotency (2) ↔ consumer duplicate delivery (3) | Integration 3.4 |
| Stale threshold unit (1) ↔ expiry semantics (7) | API 1.9 — clock fixed, fixtures straddle in the declared unit |
| Slot TTL as expiry (7) ↔ as shedding cap (6) | API 10.8 asserts both directions |
| Retry cap as read-modify-write (3) ↔ as rate cap (6) | API 8.12 |
| Missing config as fail-open (5) ↔ as drift (7) | Infra 3.1 (boot) **and** API 1.10 (runtime fail-closed) |
| Log sink: injection (5) ↔ disclosure (7) | API 6.6 (what gets written in) **and** Security 7.2 (what leaks out) |
| Client dedupe (6) ↔ client-as-untrusted (8) | UI 7.6, keyed on `(kind, id)` |
| Server-derived `preview` (8) ↔ mass assignment (5) | Security 8.1 |
| N-1 write path (4) ↔ mixed-fleet race (3) | Infra 2.4 |
| Card date (7) ↔ frontend rendering (8) | UI 1.7 |
| Sweep per-item failure (2) ↔ partial-failure visibility (7) | Integration 2.5 |
| Sweep fan-out from every replica (6) ↔ multi-instance (3) | Integration 2.6 |

**Carried forward, not closed here**: `generations` has no attempt cap, so a
permanently-failing row never reaches terminal — story 1 owns the sweep. Integration 2.7
asserts the half this story can own (one poison row does not stall other work); the cap
itself stays an OPEN in `12_MyProjects.md`.
