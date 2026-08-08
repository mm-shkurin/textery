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
- `RevisionScope` — bounded projection, `revision_number` and `document_id` only. No
  `content` (up to 200 000 units), no `source`, no `version`: the guard reads none of them,
  and the §7.x restore usecase loads the content it needs after the guard has answered.
- `DocumentRevisionRepository.find_scope_by_number_and_document(*, revision_number, document_id) -> RevisionScope | None`,
  keyword-only. No `find_by_number(n)`, extending the rule the other two ports carry.
- Revision rows carry no `owner_id`: the document is the single ownership path.
- Step 2 raises `NotFoundException(REFUSAL_MESSAGE)` importing the constant from
  `document.resolve_owned_document`, so all three guards' refusals cannot drift apart.
- **The valid range is the storage range, checked before the repository is called.**
  `revision_number` is int4-bounded (`1 .. 2147483647`); anything outside is the canonical
  refusal with the repository asked zero times. Python ints are unbounded and the column is
  not, so passing the raw value through would reach the driver as a numeric-out-of-range
  error and surface as a 500 — which the restore contract forbids ("overflowing → 404").
- Refusal logging: one id-free message, structured `extra` fields, causes
  `"document-scope-refused"` (step 1, no ids at all) and `"revision-scope-refused"` (step 2,
  carries only the caller-owned `document_id`, never the probed revision number).
- `document_revisions.document_id` is `ON DELETE CASCADE` to `documents`, and the
  constraint is pinned by a test — 1.2 shipped the equivalent FK and PK on `ai_edits`
  unpinned, which its own review pass flagged.

## Edge Cases

| Case | Behavior |
|------|----------|
| Document unresolvable (absent or foreign) | Refused at step 1; the revision port is called **zero** times |
| Real revision number, wrong document of the same owner | 404, byte-identical to the absent-document refusal, and neither document gains a version |
| `revision_number` zero, negative, or above the int4 bound | Canonical 404 from the range check, repository never called. The rest-layer non-integer edge (FastAPI would answer 422) is §1.4's |
| Either repository raises or times out | Propagates unchanged and emits **no** refusal record — an outage rendered as the canonical 404 would hide the incident and read as a probing campaign in the one channel built to attribute refusals |
| Success | Emits neither refusal cause; the causes are only trustworthy as an operability signal if the happy path is silent |
| Ownership changing between step 1 and step 2 | No window: the codebase has no document delete route and no owner-transfer usecase. If either lands, this helper is the one place the cross-check belongs |
| Document in a non-live state (archived, soft-deleted) | Does not arise: `Document` mints only `DRAFT_STATUS`. Re-decide here the day a lifecycle state lands |
