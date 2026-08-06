# Auto-generate: реферат

## Brief Description

A реферат is generated as a реферат, not as a доклад under a different label: the LLM
prompt gains a per-type template built in the domain, and the "Реферат" card becomes
selectable.

## Flow

1. User opens the document-type modal; the "Реферат" card is active (no "скоро" badge).
2. User picks it and fills the existing generation form — no new fields.
3. `POST /generations` with `document_type=реферат` behaves exactly as it does for
   доклад (201, `pending`, enqueued).
4. Worker builds the prompt through the domain prompt builder, keyed by
   `generation.document_type`.
5. For `реферат` the template asks for: введение (актуальность темы, цель работы) →
   разделы по теме → заключение (выводы), and forbids a список литературы.
6. The built prompt is handed to the provider, which sends it unchanged.
7. Status/polling/result retrieval are unchanged from story 1.

## Acceptance Criteria

- The "Реферат" card is selectable and a full generation completes end to end with
  `document_type=реферат` (against the stub provider in tests).
- The prompt for `реферат` names введение, разделы and заключение, and instructs the
  model not to produce a список литературы.
- The prompt for `доклад` is byte-identical to what the provider sent before this story —
  the refactor changes where it is built, not what it says.
- Every value in `SUPPORTED_DOCUMENT_TYPES` yields a non-empty prompt; no type falls
  through to a catch-all.
- A topic carrying prompt-injection text does not displace the template's instructions.
- The provider no longer composes prompt text; it sends what it is given.

## Validation Rules

| Field | Rule |
|-------|------|
| document_type | `"реферат"` accepted (already on the domain allowlist); unsupported values still 422 |
| topic | unchanged from story 1 — required, trimmed, max 300 chars |
| volume_pages | unchanged — required, integer, 1–10. No per-type range |
| requirements / extra_wishes | unchanged — optional, max 2000 chars each |

## Screen States

Unchanged from story 1 except the type modal. Reference:
`.memory-bank/figma/Generation screen.png`.

- **Modal — document type select**: "Реферат" loses its disabled/"скоро" treatment and
  becomes selectable alongside "Доклад". Эссе and Сочинение stay disabled until #2/#3.
- Form, chat-pending, completed and failed screens already decline per type via
  `shared/documentTypes.ts` (`Тема реферата`, `Готовим ваш реферат`, `ИИ пишет реферат`)
  — no new copy, but these strings must be asserted for реферат, not only доклад.

## Core Requirements

- The prompt template table lives in `backend/domain`, keyed by document type. The
  GigaChat adapter receives a built prompt and sends it — it composes no text.
- The доклад entry holds today's string verbatim
  (`"{document_type} на тему: {topic} ({volume_pages} стр.)"`). This story does not
  change what a доклад generates.
- The builder is **exhaustive over `SUPPORTED_DOCUMENT_TYPES`** with no catch-all
  default: a type without a template must fail a test, not fail a user's generation at
  worker time (where it would burn the retry budget and land in `failed`).
- The builder is a pure, stateless function — no module-level cache, no per-instance
  state (the backend runs as multiple instances).
- User-supplied text (`topic`, `requirements`, `extra_wishes`) enters the prompt as
  delimited data, not as instructions: the template's structural directives must survive
  a topic that tries to override them.
- The prompt must not be logged verbatim at info level — it carries the user's topic and
  wishes.
- Prompt length stays bounded by the existing field caps; the template adds a fixed
  overhead, asserted at maximum-length inputs.
- Card availability is **UX only**. The server's allowlist already accepts all four
  types, so эссе and сочинение remain reachable over the API before their stories ship —
  accepted deliberately, not an oversight to be "fixed" with a server-side gate.
