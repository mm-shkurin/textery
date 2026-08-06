# Interview — Story 2: Auto-generate: эссе

## Scope

Same shape as story 4 (реферат) — read that interview first, it establishes the
per-type-prompt design this story reuses. Story 1 already made the whole stack generic
over `document_type`; what is missing is that an эссе reads exactly like a доклад,
because one prompt serves all four types.

In scope:

- The эссе entry in the domain prompt template table.
- `available: true` for the "Эссе" card.
- Backend + frontend + acceptance coverage for the эссе path.

Out of scope:

- Everything story 4 excluded: титульник, содержание, список литературы, per-type volume
  ranges, per-type input fields.
- The generic prompt-builder mechanism itself, if story 4 ships first — this story then
  adds a table entry, not a component. If this story somehow runs first, it builds the
  mechanism and #4/#3 inherit it.

## Key Architectural Decisions

Inherited from story 4, unchanged:

- DECISION: the template lives in `backend/domain`, keyed by document type. The GigaChat
  adapter sends a prompt it did not build.
- DECISION: доклад keeps its current one-line prompt — its cell in the table holds
  today's string verbatim. Not this story's call to change.
- DECISION: `volume_pages ∈ [1, 10]` unchanged. No per-type range.
- DECISION: the request DTO is untouched — эссе adds no input field.

## Business Rules & Constraints

- Structure of an эссе: **введение → разделы → заключение, but softer than a реферат.**
  The user's words: "как реферат, мягче."
- Concretely, what "мягче" means in the prompt: the same three-part skeleton, without
  academic formality — no numbered sections, no research register. Reasoning and the
  author's own line of thought carry the text, not a survey of the topic.
- The prompt forbids inventing a список литературы, same as реферат. An эссе has no
  bibliography by form, so this is belt-and-braces rather than the central rule it is
  for реферат.
- OPEN: the эссе and реферат templates must differ enough that a reader can tell them
  apart. If the two prompts come out near-identical when written, that is a signal the
  "мягче" instruction is too weak — raise it during `/story` rather than shipping two
  types that generate the same text.

## Already Implemented (REUSE)

Identical to story 4 — the type is already accepted end to end:

| What | Where |
|------|-------|
| Domain allowlist includes `эссе` | `backend/domain/src/document/document_type.py` |
| `Generation` validates against that allowlist | `backend/domain/src/generation/generation.py` |
| REST accepts `document_type`, 422 otherwise | `backend/adapters/rest/` |
| DB check constraint | `backend/adapters/db/migrations/versions/a7b8c9d0e1f2_documents_table.py` |
| Declensions and screen copy for эссе (`эссе` in every case, plus `ваше эссе`) | `frontend/src/shared/documentTypes.ts` |

Note the frontend already declines эссе correctly in all positions — эссе is
indeclinable, and the tables account for that.

## NOT Yet Implemented (Gaps)

- The эссе template in the domain builder.
- `available: true` for `essay` in `DOCUMENT_TYPES` — currently `false`, so the card is
  disabled.
- Acceptance coverage of the эссе path.

## Cross-Story Dependencies

- Shares the prompt-builder mechanism with #4 (реферат) and #3 (сочинение). Whichever
  runs first builds it. Planned order: #4 → #2 → #3.
- Independent of #1's remaining work — same "go independent" decision as story 4.
- Touches `frontend/src/shared/documentTypes.ts` (the `available` flag only), which other
  in-flight stories also read.

## Testing Considerations

- Domain unit tests pin the эссе prompt text — the only place the per-type behaviour is
  observable without a live model.
- Acceptance runs end to end against the stub provider. No live GigaChat call in the
  automated suite.
- ACTION during `/test-spec`: include a test that the эссе and реферат prompts are not
  equal. Two types silently sharing a template is the exact failure this story exists to
  prevent, and per-type tests in separate files would each stay green through it.
