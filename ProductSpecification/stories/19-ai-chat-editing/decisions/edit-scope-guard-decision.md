# Decision: Edit-scope guard for the three edit-id-carrying endpoints

**Date**: 2026-07-31 **Scenarios**: 1.2 (binding on 1.3, 4.x, 5.x, Security 1.2)

The path document id is authoritative, so an edit the caller legitimately owns must still be
refused under another of their own documents — and the refusal has to be byte-identical to
the absent-document one, which rules out every shape that answers the edit lookup first.

| Rejected | Why |
|----------|-----|
| One composite port method joining `ai_edits` to `documents` (`find_edit_scope_by_id_document_and_owner`) | Moves the ownership policy into adapter SQL, and the shared document guard stops being the first statement of the usecase — the seven story-19 usecases then diverge in where authorization lives. Unusable by the four routes that carry no edit id |
| No helper — each of stream / state / cancel queries `(edit_id, document_id)` and raises inline | Three independent authors, three chances to validate before resolving (the failure `document-scope-guard-decision.md` rejected structural-only scoping for), and the refusal literal duplicated three times |

**Chosen**: `resolve_owned_edit` — a second shared usecase-layer helper, deliberately not a
usecase, layered on `resolve_owned_document` and called as the first statement of the three
edit-scoped usecases.

## Model

- `resolve_owned_edit(document_repository, ai_edit_repository, document_id, edit_id, owner_id) -> AiEditScope`.
  Step 1 is `resolve_owned_document`; step 2 is the edit lookup. A document the caller does
  not own never reaches step 2 — the edit lookup is itself an unauthorized read otherwise.
- `AiEditScope` — bounded projection, `id` and `document_id` only. No instruction text, no
  diff, no generated content: nothing on the guard path needs them, and a field that no
  statement reads is a field that can only leak.
- `AiEditRepository.find_scope_by_id_and_document(edit_id, document_id) -> AiEditScope | None`.
  There is deliberately no `find_by_id(edit_id)`, extending the same rule
  `DocumentRepository` carries.
- The edit row gets **no** `owner_id`. The document is the single ownership path; a second
  owner column is a second source of truth that can disagree.
- Step 2 raises `NotFoundException(REFUSAL_MESSAGE)` importing the constant from
  `resolve_owned_document` — one literal, so 1.1's and 1.2's refusals cannot drift apart.

## Edge Cases

| Case | Behavior |
|------|----------|
| Document unresolvable (absent or foreign) | Refused at step 1; the AI-edit port is called **zero** times |
| Real edit id, wrong document of the same owner | 404, byte-identical to the absent-document refusal, and the edit is unmutated under its own document — `/cancel` is one of the three routes |
| Either repository raises or times out | The error propagates. Never rendered as the canonical 404 — an outage that reads as "document not found" hides the incident and passes the byte-identity assertion |
| Refusal logging | Step 2 emits its own record with a cause discriminator distinct from step 1's, carrying only the caller's **own** ids. Indistinguishable to the caller, attributable on the server: a cross-document probe against a real edit id is otherwise invisible |
| Ownership changing between step 1 and step 2 | No window: the codebase has no document delete and no owner transfer. If either lands, this helper is the one place the cross-check belongs |
