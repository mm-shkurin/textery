# Decision: Revision-scope guard for the restore endpoint

**Date**: 2026-08-08 **Scenarios**: 1.3 (binding on 1.4, 7.x, Security 1.3)

The path document id is authoritative for revision numbers too, so a revision the caller
legitimately owns must still be refused under another of their own documents — and the
refusal has to be byte-identical to the absent-document one, which rules out every shape
that answers the revision lookup first.

| Rejected | Why |
|----------|-----|
| One parametric child-scope resolver shared by edit and revision | The child key types differ (UUID vs int), the log causes differ and the scopes differ; the parameterisation is wider than the duplication it removes, and it re-opens a helper 1.2 already froze |
| One composite port method joining `document_revisions` to `documents` | Moves the ownership policy into adapter SQL, and the shared document guard stops being the first statement of the usecase — the same reason `edit-scope-guard-decision.md` rejected it for edits |
| No helper — the restore usecase queries `(revision_number, document_id)` inline | One author today, but the refusal literal and the two-step ordering duplicate the moment §7's list route needs the same scoping |

**Chosen**: `resolve_owned_revision` — a third shared usecase-layer helper, deliberately
not a usecase, layered on `resolve_owned_document` and called as the first statement of
the restore usecase.

## Model

- `resolve_owned_revision(document_repository, revision_repository, *, document_id, revision_number, owner_id) -> RevisionScope`.
  Step 1 is `resolve_owned_document`; step 2 is the revision lookup. A document the caller
  does not own never reaches step 2.
- `RevisionScope` — bounded projection, `id`, `revision_number` and `document_id` only. No
  `content` (up to 200 000 units), no `source`, no `version`: the guard reads none of them,
  and the §7.x restore usecase loads the content it needs after the guard has answered.
- `DocumentRevisionRepository.find_scope_by_number_and_document(*, revision_number, document_id) -> RevisionScope | None`,
  keyword-only. No `find_by_number(n)`, extending the rule the other two ports carry.
- Revision rows carry no `owner_id`: the document is the single ownership path.
- Step 2 raises `NotFoundException(REFUSAL_MESSAGE)` importing the constant from
  `document.resolve_owned_document`, so all three guards' refusals cannot drift apart.
- **The valid range is the storage range, checked before the repository is called.**
  The migration declares the column `INTEGER`, so the range is `1 .. 2147483647`; the
  constant and the column type are pinned together by a test, since "the valid range is the
  storage range" is false and undetected the moment one of them moves. Anything outside is
  the canonical refusal with the repository asked zero times. Python ints are unbounded and
  the column is not, so passing the raw value through would reach the driver as a
  numeric-out-of-range error and surface as a 500 — which the restore contract forbids
  ("overflowing → 404"). The parameter reaches the guard as a `str` (see the non-integer
  edge below), so parsing and range-checking are one step in one place.
- Refusal logging: one id-free message, structured `extra` fields, causes
  `"document-scope-refused"` (step 1, no ids at all) and `"revision-scope-refused"` (step 2,
  carries only the caller-owned `document_id`, never the probed revision number).
- `document_revisions.document_id` is `ON DELETE CASCADE` to `documents`, and the
  constraint is pinned by a test — 1.2 shipped the equivalent FK and PK on `ai_edits`
  unpinned, which its own review pass flagged.
- **`UNIQUE(document_id, revision_number)`, pinned by a test.** The `| None` return is
  `one_or_none()`-shaped, so a duplicated pair turns the finder into `MultipleResultsFound`
  — a 500 on the guard path, the same failure class the range check exists to prevent,
  arriving by a different door. Duplicates are reachable: restore writes a revision row per
  call, and two concurrent restores each computing `max(n) + 1` produce the same number.
  `ai_edits`' PK is its own UUID and inherits nothing here.
- **`RevisionScope` carries the row `id`** as well as `revision_number` and `document_id`.
  The number alone is per-document, so a §7.x content loader keyed on it is globally
  ambiguous and would copy another document's revision text into the caller's document —
  a cross-tenant leak that is also a write. The content port is `id`-keyed; there is no
  `find_by_number(n)` on either the scope or the content path.
- **The refusal record always carries `caller_id`.** "Id-free" means the log *message* and
  the peer ids — `document_id` at step 1, the revision number at step 2 — never the caller's
  own id, which is what makes the causes attributable at all. `_log_refusal` is **shared**
  with `resolve_owned_edit`, not copied: two hand-written `extra` dicts drift on exactly
  this distinction, which is why that helper has one signature for both causes.

## Edge Cases

| Case | Behavior |
|------|----------|
| Document unresolvable (absent or foreign) | Refused at step 1; the revision port is called **zero** times |
| Real revision number, wrong document of the same owner | 404, byte-identical to the absent-document refusal, and neither document gains a version |
| `revision_number` zero, negative, or above the int4 bound | Canonical 404 from the range check, repository never called |
| `revision_number` parseable but not plain ASCII digits | **Undecided, and owned by §1.4.** `_parse_in_range` delegates to `int()`, which accepts surrounding whitespace, a leading `+`, PEP-515 underscores and any Unicode decimal digit — so `" 2"`, `"+2"`, `"1_0"` (→ 10) and the Arabic-Indic `"٢"` all resolve real revisions today. Nothing cross-tenant: the document scope still holds. But the endpoint is URL-aliased, which matters the moment anything downstream caches, rate-limits, dedupes or audits by path, and §7's list route inherits the same parser. §1.4 must pin the roster `(" 2", "2 ", "+2", "1_0", "٢", "2\n")` to one decided behavior — an ASCII-strict parse refusing them, or documented acceptance — and record which here |
| `revision_number` non-integer | Canonical 404 — **not** FastAPI's default 422. The contract lists 200/401/404/409/500 with no 422 and puts "non-integer" in the 404 body, and `document_edit_router.py`'s own doctrine rejects a pre-guard 422: it discloses through the status that the request got far enough to be inspected, and path coercion fires ahead of the Bearer dependency, so an unauthenticated caller would get 422 instead of 401. The route declares the parameter as `str` and this guard parses it. §1.4 covers the edge; it does not get to accept the default |
| Either repository raises or times out | Propagates unchanged and emits **no** refusal record — an outage rendered as the canonical 404 would hide the incident and read as a probing campaign in the one channel built to attribute refusals |
| Success | Emits neither refusal cause; the causes are only trustworthy as an operability signal if the happy path is silent |
| Ownership changing between step 1 and step 2 | No window: the codebase has no document delete route and no owner-transfer usecase. If either lands, this helper is the one place the cross-check belongs |
| Document in a non-live state (archived, soft-deleted) | Does not arise: `Document` mints only `DRAFT_STATUS`. Re-decide here the day a lifecycle state lands |
