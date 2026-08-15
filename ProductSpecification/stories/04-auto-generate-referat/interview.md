# Interview — Story 4: Auto-generate: реферат

## Scope

Story 1 (доклад) already carried the generation slice end to end, and it carried it
*generically*: `document_type` is a field, not a hardcoded value. So this story is
deliberately **not** "thread a new type through the stack" — that plumbing exists and was
measured, not assumed (see Already Implemented below). What is missing is that the
generated text of a реферат is indistinguishable from a доклад: one prompt serves all
four types.

In scope:

- A per-type prompt template, so a реферат comes back as a реферат — введение / разделы
  по теме / заключение.
- Opening the "Реферат" card in the type modal (`available: true`).
- Backend + frontend + acceptance coverage for the реферат path.

Out of scope:

- Титульный лист and автособираемое содержание — they need extra input fields (вуз, ФИО,
  группа) and export-side layout the editor cannot render today. Deferred.
- **Список литературы — deliberately NOT generated.** See Business Rules.
- Per-type input fields (предмет, ГОСТ, число источников) — the request DTO stays as
  story 1 left it.
- Per-type volume ranges — see Business Rules.
- Эссе (#2) and сочинение (#3): same shape, separate stories, run after this one.

## Key Architectural Decisions

- DECISION: the prompt template lives in **`backend/domain`**, not in the GigaChat
  adapter. Rationale: the text of a реферат is product behaviour, not a vendor detail —
  it must be unit-testable without a network or a stub, and it must survive story #6
  swapping models per tariff. `gigachat_provider.generate()` becomes a dumb sender: it
  receives a built prompt and posts it.
- DECISION: the builder is **generic, keyed by document type** — one domain component
  that returns a per-type template, not a `PromptBuilder` per type. #2/#3 add a table
  entry, not a class.
- DECISION (confirmed with the user 2026-08-01): доклад keeps its current one-line
  prompt. Its entry in the new template table holds exactly today's string — moving it
  into the domain builder is a pure refactor, and this story does not change what a
  доклад generates. Giving доклад a structured template is story 1's call, made in story
  1's worktree; doing it here would collide at merge with the доклад work running in
  `textery-editor` and `textery-projects`, which has its own tests over that behaviour.
- DECISION: no per-type volume validation. `volume_pages ∈ [1, 10]` stays exactly as
  story 1 defined it — реферат reuses the same rule even though a real реферат often runs
  longer. Widening the range would touch the domain, the request DTO and the form for
  all four types; not worth it for this story.

## Business Rules & Constraints

- Structure of a реферат: **введение → разделы по теме → заключение**. No титульник, no
  содержание.
- Введение names актуальность темы and цель работы; заключение states выводы.
- **The prompt must explicitly forbid inventing a список литературы.** A model asked for
  sources produces plausible-looking books, ISBNs and DOIs that do not exist, and the
  user cannot tell. Better to ship a реферат without a bibliography than one with a
  fabricated one — the user can add real sources in the editor.
- `document_type = "реферат"` is already on the domain allowlist; no validation change.
- Everything else story 1 set — topic required, requirements/extra_wishes optional, async
  generation via arq, `pending → in_progress → completed | failed` — is unchanged.

## Already Implemented (REUSE)

Verified by reading the code, not inferred from progress files:

| What | Where | State |
|------|-------|-------|
| Domain allowlist, all four types | `backend/domain/src/document/document_type.py` | ALREADY IMPLEMENTED — `SUPPORTED_DOCUMENT_TYPES = (доклад, эссе, сочинение, реферат)` |
| `Generation` validates `document_type` against that allowlist | `backend/domain/src/generation/generation.py` | ALREADY IMPLEMENTED |
| REST accepts `document_type` on create; 422 `INVALID_DOCUMENT_TYPE` otherwise | `backend/adapters/rest/` | ALREADY IMPLEMENTED |
| DB check constraint + migration | `backend/adapters/db/migrations/versions/a7b8c9d0e1f2_documents_table.py` | ALREADY IMPLEMENTED |
| Frontend declensions (родительный/винительный/притяжательный), screen titles, wire mapping both directions | `frontend/src/shared/documentTypes.ts` | ALREADY IMPLEMENTED — every screen phrase is built per type, `реферат` included |
| Type threaded from the card through the hook to the wire | `frontend/src/app/useFlowNavigation.ts` | ALREADY IMPLEMENTED |

Consequence: a реферат can be generated through the API **today** — it just reads like a
доклад. That is the whole story.

## NOT Yet Implemented (Gaps)

- Domain prompt builder keyed by document type, with the реферат template — the only
  place a prompt exists today is `gigachat_provider.py:113`:
  `f"{generation.document_type} на тему: {generation.topic} ({generation.volume_pages} стр.)"`.
- `gigachat_provider` refactored to send a prompt it did not build.
- `available: true` for `referat` in `DOCUMENT_TYPES` — the card is currently disabled,
  so the реферат path is unreachable from the UI even though the backend serves it.
- Acceptance test covering the реферат path end to end.

## Cross-Story Dependencies

- Depends on #1 (доклад) for the generation slice. DECISION: **do not wait** for #1 to
  reach 100% — it is at 16% and being finished in other worktrees (`textery-editor`,
  `textery-projects`). Where its slice is incomplete, this story works around it and the
  conflict is settled at merge.
- Blocks nothing, but #2 (эссе) and #3 (сочинение) become nearly mechanical once the
  domain builder exists — they add a template and flip a flag.
- #6 (Model switching) will change which model receives the prompt, not the prompt. The
  domain placement above is what keeps that true.
- Touches `frontend/src/shared/documentTypes.ts`, which several other in-flight stories
  also read. Only the `available` flag changes here.

## Testing Considerations

- DECISION: no live GigaChat call in the automated suite. Domain unit tests pin the
  prompt text per type (a реферат prompt names введение/заключение and forbids a список
  литературы); acceptance runs end to end against the **stub provider**
  (`backend/adapters/generation_provider/src/provider/fake_provider.py` and the GigaChat
  fixtures already used by story 1).
- Rationale for pinning prompt *text* in unit tests: it is the only place the per-type
  behaviour is observable without a real model. A stub returns a fixture regardless of
  the prompt, so an acceptance test alone would stay green with the prompt deleted.
- No manual live-model verification step is planned for this story.

## Performance/Rate Limits

Nothing new. Generation stays async through arq; the prompt is longer than story 1's
one-liner, which raises input tokens slightly and changes no timeout or concurrency
assumption.
