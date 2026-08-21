# Story 14 — Hazard Scan Record

Two scans are recorded here. They are **not** interchangeable: the first read the spec, the
second read the tests, and a guard named in prose is not a guard a test can go red on. The
second scan exists because the first one said it would.

---

# Scan 2 — `/test-spec`, 2026-08-17

Artifact under scan: the twelve drafted files in this folder. Coverage judged **only** against
named scenarios in `tests/` — a guard named in `14_AnalyticsEventTracking_AcceptanceCriteria.md`
was explicitly *not* counted as coverage, which is what surfaced most of the findings below.

**Group set covered: 1, 2, 3, 4, 5, 6, 7, 8 — the complete `_index.md` Groups list as it stood
on this date, unchanged since scan 1.** Per the index's "A new group obligates a re-scan", this
record is current only while that list has eight entries.

One pass per group, dispatched concurrently, each carrying the twelve test files, `_index.md`
and its one group file. No group was skipped; every group returned at least one firing trigger,
so none was dismissed as a block.

## Verdicts

| Group | Verdict | GAPs | Notable dismissals |
|-------|---------|------|--------------------|
| 1 — Money, numbers & representation | GAPS | 9 | currency half dead; no division or rounding; timeout units covered from both sides |
| 2 — Re-run safety, ordering & atomicity | GAPS | 8 | inbound duplicate direction genuinely strong; gaps are all on the other half of each guard |
| 3 — Concurrency, consistency & distribution | GAPS | 9 | no read replica, no cache; dead-letter n/a (no queue); outbox refusal pinned by a scenario |
| 4 — Data lifecycle & schema | GAPS | 10 | events are append-only (no transition matrix); downgrade no worse than its 22 predecessors |
| 5 — Request boundary & input | GAPS | 7 | SQL injection (parameterized); sort/filter allow-list (no read surface); shell sink (no process invocation) |
| 6 — Scale & resource limits | GAPS | 6 | no cache stampede; no batch endpoint; retention deferral is not a guard |
| 7 — Time, operability & disclosure | GAPS | 14 | local-day bucketing (UTC instants only); token-expiry instant is pre-existing |
| 8 — Client / frontend | GAPS | 5 | optimistic render (nothing rendered ahead of the server); unsaved-input loss from a new field |

**68 raw GAPs, heavily overlapping.** After synthesis, folded as **60 new scenarios** across the
six category files (108 → 168), plus five existing scenarios rewritten to be assertable and
five marked ⚠ BLOCKED on an open contract decision. Every fold is critical-path; none went to
`extended/`. The count exceeds the GAP count because several single GAPs needed more than one
scenario to close — the dedup seam alone took three, since one scenario per hazard would have
let a per-process implementation pass.

## What the second scan found that the first could not

Scan 1 read the spec and folded 85 findings into the acceptance-criteria file. Scan 2 read the
tests and found that **a large share of those folded guards never became scenarios**. Six
passes independently reported the same shape: the criteria file names the guard in prose, and
nothing in `tests/` would go red on it. Examples, each now folded:

- "Fail the second OAuth emission … the record names which half failed" → no scenario (now API 8.7)
- "An orphaned start is detectable … silence must not be the only evidence" → no scenario (now Infra 1.4)
- "A rejected send increments a distinguishable drop signal" → no scenario (now UI 4.7)
- "A None account id updates zero rows, never the whole table" → no scenario (now API 11.8)
- "One set-based UPDATE regardless of N" → no scenario (now API 11.7)
- "An ASCII fixture can never go red on a swapped unit" → every bound fixture was unit-blind (now API 3.5 and 7.12)
- "Dispatch A then B, resolve B first, still orderable" → no scenario (now UI 3.6)
- "Tested under the Turkish locale the repo already parameterizes" → no scenario (now API 7.13)

This is the catalogue's own premise demonstrated: redundant application across steps is the
point, and a same-kind gate at the test-spec step would have read these files as complete.

## Seam synthesis

| Seam | Passes | Resolution — the single guard that owns it |
|------|--------|--------------------------------------------|
| Dedup marker: sequential replay vs. concurrent vs. cross-instance | 2, 3 | Three scenarios, not one — API 5.1 (sequential), 5.4 (cross-instance + restart), 5.5 (same-instant interleave). 5.1 must **not** be counted as closing the other two: a per-process set passes it, and a read-then-insert passes 5.1 and 5.4. |
| Client dispatch order vs. arrival-assigned `sequence` | 2, 3, 8 | Scan 1 resolved clock skew by making `sequence` DB-assigned on arrival. That does **not** answer this: arrival order is the wrong order when the second send wins the race. UI 3.6 owns it and forces the design choice (dispatch-ordered emission or a client-carried ordinal). |
| Pool configuration: magnitude vs. named vs. declared vs. boot-validated | 6, 7 | Infra 3.3 owns the ceiling and the behavioural check, 3.2 the declaration in both compose files, 3.4 the named defaults. **Revised 2026-08-19:** the pool is no longer this story's to set — 3.3 reads the ceiling off the configured engine, and 3.4 asserts named defaults rather than a failed boot. |
| Rate limiter: direction vs. key space vs. cross-instance vs. rollover vs. hang | 2, 3, 5, 6, 7 | API 6.3 (fails closed), 6.2 (separate key space), 6.4 (one budget across instances), 6.5 (rollover at a fixed clock), 6.6 (hang), 6.7 (refusals signalled), Sec 5.5 (pruning spares live and OAuth rows). |
| Bounds: unit vs. magnitude vs. named config | 1, 6, 7 | Group 1 owns the unit — API 3.5 (bytes) and 7.12 (characters), each with a fixture that differs in the two representations. Group 6 owns the magnitude, group 7 that the value is named and reported at startup, with a named default (Infra 3.4). |
| Deletion completeness: FK vs. eraser vs. ORM vs. scope vs. cost | 3, 4, 6, 7, 8 | API 11.4 (raw SQL / N-1 path), 11.9 (object-model path — the one a delete-cascade would pass), 11.8 (absent scope), 11.7 (statement count at volume), 11.6 (interleave pinned between detach and removal). |
| PII: containment vs. the counter table | 1, 5, 7 | Sec 5.1 now reads the counter rows too, and Sec 5.2 forces the decision. The story's headline claim was contradicted by its own bucket key. |
| Partial-failure visibility vs. "invisible to the visitor" | 7, 8 | UI 4.7 carries both halves in one scenario, because they fail together: attempt count (no herd on recovery) and drop signal (a broken route must not look like a quiet day). |
| Sweep: fan-out vs. overlap vs. batch size | 3, 6 | API 9.4 + Load-Ext 2.1 (M instances, one tick), Infra 4.1 (one activation outlasting its interval — the count assertion cannot catch a double requeue, since requeue emits nothing). Load 3.1 (bounded batch) is `[S]` out of scope for Story 14 — task 7. |
| Encoding at the sink (CSV / HTML) | 1, 5 | Explicitly **not** Story 14's. Sec 3.1 and the new 3.2 assert verbatim storage for the attribution values **and** the payload, so Story 15's sink-side escape is not pre-defeated by an input-side transform. |

## Open decisions — CLOSED 2026-08-19

All five are now recorded in `endpoints.md` § "The five decisions the test spec was blocked
on", and every ⚠ BLOCKED marker in `tests/` has been replaced by a literal asserted outcome.
Four were answered by the product owner on 2026-08-17; the fourth and the shape of the third
were then settled by the developer decision of 2026-08-19 (`A1 + B2` — analytics is fail-open
and never changes an existing route's answer), and the fifth by the same decision's
minimum-change principle.

| # | Decision taken | Where the scenario now asserts it |
|---|---|---|
| 1 | Absent / null / `{}` payload all store `{}`; column `NOT NULL` default `{}` | `extended/01` §1.1 |
| 2 | Same key + same event name → `204` replay; same key + different event name → `409`, nothing stored; key unique per visitor | `extended/01` §3.1 |
| 3 | An undecodable campaign parameter is not frozen and not stored; the operation is unaffected | `extended/02` §2.1, API §7.8 |
| 4 | Over-bound campaign parameters are dropped as a set; register and handshake answer exactly as before | API §7.5, §7.5a, §7.12, `extended/05` §3.1, `extended/06` §2.4, `extended/02` §2.2 |
| 5 | `analytics_events.visitor_id` is nullable; no sentinel, no dropped event; the ingest route still requires one | `04_Infrastructure_Tests.md` §1.4a |

Three guards were **revised** rather than merely unblocked, because the developer decision
overrode what the scan had folded. Recorded here so the change is not mistaken for drift:

| Guard as scanned | Guard now | Why |
|---|---|---|
| Over-bound `utm_*` → `400` on `/auth/register` | dropped as a set, no `400` | A hazard scan optimizing for input strictness produced a new refusal reason on the product's most sensitive route — the thing the story's own isolation criterion forbids. Strictness on an *existing* route is not free; it is a behaviour change. |
| GeoIP variable absent → boot fails fast | boots, resolution disabled, one named startup record | The `JWT_SECRET` pattern fits a variable that gates a working product, not one that gates a nullable analytics column. The signal is kept; the process exit is not. |
| This story sets `pool_size` / `max_overflow` / `pool_timeout` explicitly | reads them off the engine; `session.py` unchanged | Re-tuning every existing endpoint's connection behaviour is not an analytics story's call to make on a prediction. The load scenarios measure against the real pool and can motivate the change with data. |
| Two more scenarios reached beyond the story: the document-open control gaining a busy state (UI 3.4) and a hostile `User-Agent` refusing a registration (Sec 4.3) | both assert the existing behaviour is kept, and that the analytics outcome is reached without new UI or a new refusal | Same rule as the `utm_*` `400`: strictness on an existing surface is a behaviour change, not free hardening. |

One scenario could **not** be adapted and is now **`[S]` out of scope — decided 2026-08-19**:
`03_Load_Tests.md` §3.1, which requires a `LIMIT` on `list_stale`. The sweep's unbounded query
is a real pre-existing risk, but bounding it changes existing behaviour and Story 14 does not
need it (the requeue path emits nothing). It is carried as technical debt in
`ProductSpecification/tasks/7-refactoring-bound-stale-generation-sweep/`, not fixed on the way
past. `Load-Ext` §2.1 (sweep fan-out) is **unaffected** — it asserts one event per generation
across instances and needs no batch limit.

The original five, for the record:

1. **Payload absent vs. explicit null vs. empty object** — three inputs, one stored
   representation each. `extended/01` §1.1.
2. **One occurrence key reused under a different event name** — refuse, or store a second row.
   `extended/01` §3.1.
3. **A campaign parameter that decodes to replacement characters** (a cp1251 marketing link) —
   refuse so a later valid visit can still be the first touch, or store and document. The
   acceptance criteria deliberately left this open. `extended/02` §2.1.
4. **Over-bound campaign parameters on the handshake** — the criteria say refuse; the scenario
   also demands the visitor is never left on a broken sign-in. On a redirect route those
   conflict, so one must give. `extended/02` §2.2, `extended/06` §2.4.
5. **A generation with no recorded visitor** — the event's visitor column is `NOT NULL`, and
   every generation in flight across the migration has none. Sentinel visitor, omitted event,
   or nullable column. `04_Infrastructure_Tests.md` §1.4a.

Decisions 1–4 are contract calls; 5 is a schema call with a rolling-deploy consequence.
*(All five answered above, 2026-08-19.)*

---

# Scan 1 — `/story`, 2026-08-16

Scanned at the `/story` step against the **Groups** list in
`.claude/guidelines/hazard-catalogue/_index.md` as it stood on that date.

**Group set covered: 1, 2, 3, 4, 5, 6, 7, 8 — the complete list.**

One pass per group, dispatched concurrently, each carrying the drafted spec, `interview.md`,
`_index.md` and its one group file. No group was skipped and none was dismissed as a block:
all eight found at least one firing trigger.

## Verdicts

| Group | Verdict | GAPs | Notable dismissals |
|-------|---------|------|--------------------|
| 1 — Money, numbers & representation | GAPS | 11 | money/currency half dead; no division, rounding or float compare |
| 2 — Re-run safety, ordering & atomicity | GAPS | 8 | — (all five classes fired) |
| 3 — Concurrency, consistency & distribution | GAPS | 7 | no read replica, no cache; dead-letter n/a (no queue); periodic-job overlap n/a |
| 4 — Data lifecycle & schema | GAPS | 9 | `downgrade()` no worse than the 22 existing migrations; no purge job ships |
| 5 — Request boundary & input | GAPS | 16 | SQL injection (SQLAlchemy parameterizes); sort/filter allow-list (no read surface) |
| 6 — Scale & resource limits | GAPS | 10 | pagination as a read surface (Story 15) |
| 7 — Time, operability & disclosure | GAPS | 17 | local-day bucketing (UTC instants only) |
| 8 — Client / frontend | GAPS | 7 | optimistic render and unsaved-input loss (no visible element, no new field) |

85 raw findings, heavily overlapping. Every one folded into
`14_AnalyticsEventTracking_AcceptanceCriteria.md`, into the spec's Core Requirements /
Validation Rules, or into the Notes file's dismissal list.

> **Correction from scan 2:** "folded into the acceptance-criteria file" turned out not to mean
> "will be tested". Scan 2 found a large share of these guards had no scenario that would go red
> on them. The criteria file is a good record of *what was decided*; it is not a test plan, and
> the two scans together are what makes that visible.

Scan 1's periodic-job-overlap dismissal is also **overturned** by scan 2 (group 3): the sweep's
mutual exclusion was dismissed as "already made mutually exclusive by the storage CAS", which
covers two instances on one tick but not one activation outlasting its own interval. Now
guarded by `04_Infrastructure_Tests.md` §4.1.

## Seam synthesis

| Seam | Passes | Resolution — the single guard that owns it |
|------|--------|--------------------------------------------|
| Ordering vs. clock vs. testability | 1, 3, 7 | Split the two jobs: `event_time` from the injected `Clock`, `sequence` DB-assigned as the total-order key. |
| Transaction boundary vs. idempotency vs. async delivery | 2, 3, 4 | Emission runs after the caller's commit, on its own session, only from the code path that won the persisted transition. |
| Duplicate `GENERATION_STARTED` (sweep vs. retry) | 2, 3, 4, 6 | The requeue path emits nothing; `RetryGeneration` emits only when `created`. |
| `visitor_id` transport into the background task | 2, 3, 6, 8 | A column on `generations`, written by `RequestGeneration`. |
| The four dark event names | 4, 5, 8 | The route's enforced set narrows to the three client-origin names; the CHECK still lists all 12. |
| Bounds: unit vs. magnitude vs. config | 1, 6, 7 | Every bound is a number, with its unit, from named config, tested at limit and limit+1. |
| Rate limiter: direction vs. size vs. key space | 3, 5, 6, 7 | Fails closed, own key space, named limit/window, elapsed windows pruned. |
| Deletion completeness | 3, 4, 5, 6, 7, 8 | `ON DELETE SET NULL` + one set-based scoped UPDATE + key-scoped client erasure. |
| PII: containment vs. echo vs. logs | 1, 5, 7 | One sentinel test spanning storage, response bodies and captured logs. |
| Client double-fire vs. server dedupe | 2, 8 | A client-minted occurrence key collapsed server-side. |
| Encoding at the sink (CSV / HTML) | 1, 5 | Explicitly not Story 14's; handed to Story 15 in writing. |

## Disposition of the one requirement that changed the interview's wording

The interview left the `visitor_id` transport mechanism to `/design-preview` and described the
ingest endpoint as accepting the contract's names. The scan settled both — see the Notes file's
"Additional Context". Neither reverses a product-owner decision; both narrow a design choice
the interview had explicitly left open.
