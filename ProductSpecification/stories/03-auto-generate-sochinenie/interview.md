# Interview — Story 3: Auto-generate: сочинение

## Scope

The largest of the three type stories. It reuses the per-type prompt design from story 4
(реферат) **and** adds the first per-type input field the product has — «произведение /
автор». Read story 4's interview first for the shared design.

In scope:

- The сочинение entry in the domain prompt template table.
- A new **optional** request field naming the literary work the сочинение is written
  about, threaded from the form to the prompt: DTO, domain, DB migration, form.
- `available: true` for the "Сочинение" card.
- Backend + frontend + acceptance coverage.

Out of scope:

- Титульник, содержание, список литературы, per-type volume ranges (same exclusions as
  story 4).
- Making the new field visible to доклад / реферат / эссе — see the visibility decision
  below.

## Key Architectural Decisions

Inherited from story 4:

- DECISION: template lives in `backend/domain`, keyed by document type; the GigaChat
  adapter sends a prompt it did not build.
- DECISION: доклад keeps its current one-line prompt.
- DECISION: `volume_pages ∈ [1, 10]` unchanged.

New to this story:

- DECISION: сочинение gets a dedicated request field for the литературное произведение /
  автор. It is **optional** — an empty value is valid and produces a free-standing
  рассуждение на тему; a filled value makes the arguments lean on that text. Rationale:
  optional keeps the domain rule uniform (no "required only for one type" branch), and
  existing rows migrate without a backfill.
- DECISION: the field is shown in the form **only when the selected type is сочинение**.
  Доклад / реферат / эссе never see it. Rationale: a generic "источник" field on a
  доклад form is noise the user has to skip past on every generation.
- DECISION (confirmed with the user 2026-08-01): the wire name is **`source_work`**. It
  sits beside `topic`, `volume_pages`, `requirements`, `extra_wishes` in
  `GenerationRequestDto` (`backend/adapters/rest/src/dto/generation/`) and reads the same
  way they do. Fixed now rather than during `/api-spec`, because renaming it after the
  contract ships breaks every client.
- CONSEQUENCE, stated plainly: this field is the reason story 3 is bigger than #2 and #4.
  It touches the request DTO, the `Generation` entity, a new Alembic migration, the
  response projections that echo request fields, the form, and every test layer. #2 and
  #4 touch a prompt table and a boolean.

## Business Rules & Constraints

- Structure of a сочинение: **введение по проблеме → аргумент 1 → аргумент 2 →
  аргумент 3 → заключение.** The user's exact words; three arguments, not "a few".
- School register — plain language, not the academic tone of a реферат.
- When the произведение field is filled, the arguments must draw on that text; when it is
  empty, the сочинение is a рассуждение on the topic alone. One template, two branches.
- The prompt forbids inventing a список литературы (inherited from story 4). Quoting the
  named произведение is not a bibliography and is not covered by that ban — but note the
  same hazard applies: a model asked for a citation invents page numbers. Do not ask the
  prompt for citations with page references.
- Field validation: optional string, length-capped like the other free-text fields.
  Empty string and absent are equivalent.

## Already Implemented (REUSE)

| What | Where |
|------|-------|
| Domain allowlist includes `сочинение` | `backend/domain/src/document/document_type.py` |
| `Generation` validates against that allowlist | `backend/domain/src/generation/generation.py` |
| REST accepts `document_type`, 422 otherwise | `backend/adapters/rest/` |
| DB check constraint | `backend/adapters/db/migrations/versions/a7b8c9d0e1f2_documents_table.py` |
| Declensions and screen copy (`сочинения`, `ваше сочинение`) | `frontend/src/shared/documentTypes.ts` |
| Optional-free-text field precedent (`requirements`, `extra_wishes`) — DTO, entity, storage, form all already carry two of them | `GenerationRequestDto` in `backend/adapters/rest/src/dto/generation/` |

That last row matters: the new field is not a new *kind* of thing. It is a third optional
free-text field, and the two existing ones are the pattern to copy — including how they
are stored and echoed back.

## NOT Yet Implemented (Gaps)

- The сочинение template in the domain builder, with its filled/empty branch.
- The произведение field: DTO, `Generation` entity, Alembic migration, storage mapping,
  response projection.
- Conditional rendering of the field in the generation form.
- `available: true` for `sochinenie` in `DOCUMENT_TYPES`.
- Acceptance coverage of both branches (with and without the произведение).

## Cross-Story Dependencies

- Shares the prompt-builder mechanism with #4 and #2. Planned order #4 → #2 → #3, so this
  story inherits it rather than building it.
- Adds a column to `generations`. Other in-flight stories (#17 export, #18 generate→edit,
  #19 AI chat editing) run against the same table in their own worktrees — the migration
  must be additive and nullable so their branches merge without a conflict.
- Touches `frontend/src/shared/documentTypes.ts` (the `available` flag) and the
  generation form, which #18 is actively reworking. Expect a merge conversation there.

## Testing Considerations

- Domain unit tests pin the сочинение prompt for **both** branches — произведение named
  and произведение absent. One test over the filled branch alone would stay green if the
  empty branch produced a broken prompt.
- Acceptance runs end to end against the stub provider; no live GigaChat call.
- ACTION during `/test-spec`: a test that the four type prompts are pairwise distinct
  (extends the эссе/реферат check named in story 2's interview to the full set).
- DB-level test that an existing row without the new column still loads — the migration is
  additive and nullable, and nothing else guarantees old generations keep working.
