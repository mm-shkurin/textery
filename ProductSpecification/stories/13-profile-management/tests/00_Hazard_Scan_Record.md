# Hazard Scan Record — Story 13 (Profile management)

Two scans, both recorded here: the `/story` scan over the drafted spec (below), and the
`/test-spec` scan over the drafted test files (at the end of this file). Per `_index.md` the
catalogue is applied from scratch at every step that references it — the second scan does not
trust the first, and it found 26 gaps the first could not have found, because its artifact is
the set of named scenarios rather than the prose they were written from.

## Scan 1 — `/story`

Run 2026-08-13, over the drafted spec. One `hazard-scan-agent` per group,
dispatched concurrently, followed by one synthesis pass over the index-named seams and every
seam an individual pass flagged.

**Group set covered (the `_index.md` Groups list at scan time): 1–8.** If a group 9 is ever
added, this spec is stale until re-scanned — per `_index.md`, "a spec whose recorded group set
is a strict subset of the current Groups list is stale".

## Verdicts

| Group | Verdict | GAPs | Covered |
|-------|---------|------|---------|
| 1 Money, numbers & representation | GAPS | 6 | 0 |
| 2 Re-run safety, ordering & atomicity | GAPS | 3 | 3 partial |
| 3 Concurrency, consistency & distribution | GAPS | 5 | 3 |
| 4 Data lifecycle & schema | GAPS | 6 | 1 |
| 5 Request boundary & input | GAPS | 5 | 0 |
| 6 Scale & resource limits | GAPS | 4 | 2 |
| 7 Time, operability & disclosure | GAPS | 4 clusters | 1 |
| 8 Client / frontend | GAPS | 6 | 4 |

**35 GAPs, all folded** into `13_ProfileManagement.md` (Validation Rules / Core Requirements)
and `13_ProfileManagement_AcceptanceCriteria.md` (named guards). **None dismissed.**

No group was out of altitude. Dismissed *sub-triggers*, with reasons, are recorded in the
individual passes: currency and arithmetic (group 1); compute-then-commit ordering and deadline
budgets, the chain being one hop deep (group 2); all async-delivery classes and read-replica
splits, no queue or replica existing (group 3); parent-child deletion and confirm-intent, this
story deleting nothing (group 4); SQL injection, SQLAlchemy parameterizing (group 5); pagination
and cursor stability, neither route paging and the migration having no backfill (group 6);
new env vars and flags, the story introducing none (group 7); optimistic render, nothing being
drawn before the server confirms (group 8).

## Seams closed in synthesis

Several GAPs were the same hazard seen from two sides. Synthesis named one guard per seam and
confirmed which side carries it, rather than letting each pass assume the other owned it.

| Seam | Passes | Single guard |
|------|--------|--------------|
| Rename rewrites status columns | 4 (blind write) + 3 (lost update) | The UPDATE sets only `name` — SQL-shape capture, plus a whole-row re-read after renaming a verified account |
| Invisible / blank name | 1 + 4 + 5 | Blankness is modelled on `required_topic()` (`generation_validation.py`) but stricter: whitespace + `Cf` + named invisible non-format code points, and `Cc`/`Cs` refused outright. Blank clears to NULL, so "no name" has one representation. Widened at `/api-spec` — the borrowed predicate let U+3164 persist as an unrenderable name and let a NUL (U+0000) reach Postgres as a 500 |
| Write actually reaches Postgres | 1 + 2 + 3 + 7 | One db test: real Postgres, separate-session re-read, INSERT and UPDATE paths, maximal-astral + NFD fixture |
| Absent vs null vs empty | 4 (data loss) + 5 (parsing) | Three presence tests, plus a request model that carries presence instead of collapsing all three to `None` |
| Identity snapshot staleness | 3 + 5 + 7 + 8 | Session-generation stamping: superseded responses dropped, snapshot updated on the write path and cleared on sign-out |
| Header degraded render | 2 + 5 + 7 + 8 | Per-state defined UI, degraded visibly distinct from loading, «Выйти» functional in every state |
| `created_at` on the wire | 1 + 4 + 7 | `Z`-suffixed UTC via the existing `_as_utc` precedent; naive input raises; client date test TZ-pinned to a non-UTC zone |
| Length unit | 1 + 8 (+ OpenAPI as a third counter) | Code points everywhere — domain, client counter, and the `maxLength` written at `/api-spec` |
| `/me` request fan-out and retries | 6 + 8 | Exactly one `GET /me` per page across two mounted menus and across in-app navigation; bounded timeout, abort on unmount, capped jittered retries |
| Error-body shape | 5 + 7 | Every failure family answers `{error_code, message}`; the over-length case reaches the domain path, not Pydantic's 422, which echoes the input back |
| Migration on a live fleet | 2 + 3 + 4 + 6 | N-1 code against N schema, plus upgrade→downgrade→upgrade preserving pre-existing rows |

## Scan 1 — one finding contradicted the interview

Group 6 challenged the interview's Performance paragraph, which declined a load scenario because
the story adds no queue, no external API and no table scan. That reasoning is accurate and does
not address request rate — the binding constraint under this project's declared Throughput
profile — and this story makes `/me` the highest-rate endpoint in the product. The load scenario
is in scope; the revision is recorded in `13_ProfileManagement_AcceptanceCriteria.md` and the
Notes rather than by silently editing the interview.

---

# Scan 2 — `/test-spec`

Run 2026-08-13 over the twelve drafted test files (`01`–`06` plus `extended/`). One
`hazard-scan-agent` per group, dispatched concurrently, then one synthesis pass over the
index-named seams and every seam an individual pass flagged. The rule the passes were held
to: a hazard is covered only when a **named scenario** in those files would go red on it —
prose in the spec, a decision in `endpoints.md`, or a guard listed in the acceptance criteria
does not count.

**Group set covered: 1–8** (the `_index.md` Groups list at scan time). A group 9 makes this
spec stale until re-scanned.

## Verdicts

| Group | Verdict | GAPs | Folded | Dismissed |
|-------|---------|------|--------|-----------|
| 1 Money, numbers & representation | GAPS | 5 | 5 | 0 |
| 2 Re-run safety, ordering & atomicity | GAPS | 6 | 6 | 0 |
| 3 Concurrency, consistency & distribution | GAPS | 2 | 1 | 1 |
| 4 Data lifecycle & schema | GAPS | 4 | 4 | 0 |
| 5 Request boundary & input | GAPS | 3 | 3 | 0 |
| 6 Scale & resource limits | GAPS | 2 | 2 | 0 |
| 7 Time, operability & disclosure | GAPS | 6 | 6 | 0 |
| 8 Client / frontend | GAPS | 3 | 3 | 0 |

**26 GAPs: 25 folded as named scenarios, 1 dismissed with reason.** No group was out of
altitude.

## Dispositions

| GAP | Folded as |
|-----|-----------|
| Raw cap's unit never pinned | API 3.2a |
| OpenAPI `maxLength` — the third counter — unguarded | API 8.1 |
| `created_at` sub-second precision | API 2.6 |
| Normalization never proven to run | API 3.4a |
| Server process timezone an untested ambient | API 2.7 |
| Storage-sink metacharacters (injection dismissed by mitigation, not guard) | API 3.6a |
| Failure between write and commit | API 5.5a |
| Rename against a removed account may resurrect the row | API 5.5b |
| Redaction asserted as absence-of-string, token never treated as a secret | API 7.5, Security 5.2a |
| A redacted failure is untraceable | API 7.6 |
| Hostile locale never exercised | UI 2.4b |
| Date boundary never crossed | UI 2.4a |
| Unknown `error_code` has no defined client branch | UI 5.3a |
| Unknown extra response field (forward compatibility) | UI 6.1a |
| «Выйти» is a third, unguarded exit from a dirty form | UI 7.3a |
| A save refused as unauthorized discards typed input silently | UI 7.3b |
| Pool baseline never asserted across the refusal paths | Load 2.2 |
| A slow database (as opposed to a down one) | Infra 1.2a |
| A row written by the pre-story image during the overlap | Infra 2.2a |
| No boot-time config validation | Infra 3.0 |
| Timeout budget has no ordering check | Infra 3.0a |
| Account-existence check never driven into failure | Security 1.5 |
| The address is the second hostile value into the same sinks | Security 3.1a |
| Read-versus-read response ordering | Integration 2.2a |
| Write auto-retried / ambiguous manual retry | Integration 3.3a |
| A save the client abandons while the server commits | Integration 3.3b |
| Non-JSON (proxy HTML) answer on the read path | Integration 3.3c |
| Cross-surface staleness window undefined | Integration-ext 1.1a |
| Pathological-but-legal body shape | API-ext 1.3 |
| Unrenderable-date fallback is silent | UI-ext 3.4 |

## The one dismissal

**Lost update / stale overwrite (group 3).** The group's forced guard is a version or
`If-Match` conflict on a second stale write, and no scenario goes red on a lost update —
`extended/01_API_Tests_Extended.md` 3.1 and 3.2 assert the opposite on purpose. Dismissed
because last-write-wins is a recorded decision with its cost stated three times
(`endpoints.md` § No 409, `13_ProfileManagement.md` Core Requirements,
`13_ProfileManagement_Notes.md` Functional Warnings), and 3.1/3.2 exist precisely to pin that
behaviour as chosen rather than absent.

The pass's sharper point is kept rather than waved off: because clearing is first-class, a
stale tab can *clear* a name it never saw, which is not "one retype" — the user cannot retype
what the other tab set. That is the shape recorded in extended 3.2, and it is the argument to
revisit the decision the moment the profile grows a field where a silent overwrite matters
(the Notes already name the version column as the future move).

## Corrections to scan 1's record

- Scan 1 dismissed **deadline budgets** (group 2) as "the chain being one hop deep". The
  drafted spec contradicts that: browser → nginx → application → pool checkout → Postgres,
  each with its own timeout, multiplied by the client's capped retries. Folded as Infra 3.0a
  and Integration 3.3b.
- Scan 1 dismissed **optimistic render** (group 8). Still correct as to rollback (UI 5.1
  covers it); the neighbouring read-versus-read ordering case was not covered and is now
  Integration 2.2a.

## Seams closed in synthesis

| Seam | Passes | Single guard |
|------|--------|--------------|
| Length unit at both gates | 1 + 6 + 8 | API 3.2a (raw gate) and 3.3/3.5 + UI 3.2 (normalized gate) and API 8.1 (the published schema) — three counters, three scenarios |
| Retry policy: read versus write | 2 + 6 + 8 | Integration 3.3 caps and jitters the **read**; 3.3a states the **write** is never re-sent automatically. One policy, two directions, both named |
| Connection cleanup on the failure path | 2 + 5 + 6 | Load 2.2 owns the pool baseline across refusals; Security 1.5 owns "deny, not serve" when the existence check itself fails; Infra 1.2a owns the slow-statement case. One setup family, three distinct assertions, each attached to one file |
| Abandoned request versus identity snapshot | 2 + 3 + 8 | Integration 3.3b — the pre-existing session-generation seam covers *superseded* responses, not a response the client never receives while the effect commits |
| Redaction versus attribution | 7 (both sides) | API 7.5 and 7.6 as a pair — either alone is satisfied by an implementation that defeats the other |
| Config drift: size and time | 6 + 7 | Infra 3.1 (body caps) and 3.0a (timeout budget) share one shape: the nesting order is asserted, and inverting it fails the check |
| Contract evolution at the client | 4 + 8 | UI 5.3a (unknown failure code) and 6.1a (unknown response field) — both directions of an independently deployed pair |
| Hostile text into the identity sinks | 1 + 5 + 8 | Security 3.1 (name) and 3.1a (address) — the same three sinks, the two values that reach them |

## Obligation carried forward

The catalogue's mass-assignment guard in its full form — set two fields, update one, assert
the other kept its prior value — is unwritable while `name` is the only writable field. The
tri-state exists specifically because story 8 or story 14 adds a second one; whichever does
must arrive with that two-field guard, or the tri-state becomes decoration.
