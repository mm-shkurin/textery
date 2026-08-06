# Story 4: Auto-generate: реферат — Progress

Bootstrapped 2026-08-01 from `04_AutoGenerateReferat.md` + `tests/`. Three-file layout
from the start: this file holds the story-level narrative, decisions and the Spec
checklist; `progress-backend.md` owns Backend + Integration + Security + Load +
Infrastructure Scenarios; `progress-frontend.md` owns Frontend Scenarios.
`ProductSpecification/stories.md` is the cross-file rollup.

## Spec Phase

- [x] interview — `interview.md`
- [x] story — `04_AutoGenerateReferat.md` + `_Notes.md`, hazard-scanned against groups 1–8
- [S] mockups — the only visual change is the реферат card losing its "скоро"
  treatment; story 1's `02-type-modal` mockup already renders the four cards. No new
  screen, so no new mockup.
- [x] api-spec — no new endpoint. `generations_create.yaml` corrected: its
  `document_type` enum said `[доклад]` while the domain has accepted all four types
  since story 1 and `documents_create.yaml` already listed them. A client trusting that
  enum expected 422 for эссе and would have got 201.
- [x] test-spec — `tests/` (6 categories + extended), scan record in
  `tests/HAZARD_SCAN.md`

## Decisions Carried Into Implementation

From `interview.md`, settled before any code:

- The prompt template table lives in `backend/domain`, keyed by document type; the
  GigaChat adapter composes nothing.
- The доклад entry holds today's string verbatim. Story 1 is being finished in
  `textery-editor` and `textery-projects` against the current доклад output — perturbing
  it, even by whitespace, would redden their tests for a reason unrelated to their work.
- No список литературы is ever generated. A model asked for sources invents ISBNs the
  user cannot check.
- `volume_pages` stays `[1, 10]` for all types. No per-type range.
- The type card's `available` flag is UX. The server accepts all four types today, so
  эссе and сочинение stay reachable over the API until #2/#3 — deliberate, recorded as a
  passing security scenario so nobody "fixes" it with a gate those stories would remove.

## What Works Today (2026-08-06)

Written as capabilities rather than as a checklist — the checklists live in
`progress-backend.md`, and a reader asking "what does this story actually do yet"
should not have to reconstruct it from ticked boxes.

**The one thing to read first: none of it is wired to a real generation.** The domain
builds the prompt correctly and the usecase calls it — and then **discards the result**
(`generate_document.py:77`). `GigaChatProvider` still composes its own f-string, so a
реферат generated in production today still gets доклад-shaped wording, with no
bibliography ban and none of the refusals below. That is deliberate: substituting the
builder into the provider is Backend Scenario 2.1's behaviour, and doing it earlier would
leave 2.1 with a green adapter and nothing to redden. Everything that follows is real,
tested and inert until 2.1 lands.

**Composing a реферат prompt.** `build_prompt` is a pure domain function over a
three-field request (`document_type`, `topic`, `volume_pages`). реферат gets its own
structural template — введение with актуальность and цель, разделы по теме, заключение
with выводы — while доклад, эссе and сочинение share a plain template that is
byte-identical to the string the GigaChat adapter has been composing since story 1. That
byte-identity is asserted between the two live composers, not between two hand-typed
literals, so neither can be edited alone.

**Refusing to invent sources.** Every supported type except доклад carries a sentence
forbidding a список литературы. The scope is *derived* from `SUPPORTED_DOCUMENT_TYPES`
rather than hand-listed, so a fifth long-form type added later carries the ban with no
human step. доклад is excluded through a named freeze for story 1, not a judgement about
доклад. Note the limit of what this can prove: the ban is an instruction to a third-party
model, and no test here can show the model obeyed it — that is the open hand-judgement
below.

**Refusing to build a prompt it cannot phrase.** A `volume_pages` that is absent, zero,
negative, out of range or a boolean, and a `topic` that is absent, empty or
whitespace-only, all raise `PromptBuildError` instead of rendering `(None стр.)` or
`на тему: None` into a billed request. These are reachable because the storage hydration
path applies none of `create`'s validation, so the guard sits in the builder rather than
at the entity boundary.

**Failing a doomed generation once, cheaply.** A prompt that cannot be built is
terminal on the first failure: the provider is called **zero** times, no backoff is
awaited, and the row is written `failed` with the sanctioned message. Before this, the
retry loop spent both attempts and a backoff sleep re-phrasing an identical request from
an identical row, then billed the provider for a request that could not be phrased.

**Catching a missing template before deploy rather than at boot.** Adding a fifth
document type without its template is red in CI, via a set-equality test that `python -O`
cannot strip — where the previous guard was a bare `assert` that `-O` removes. At
runtime a missing template is a scoped `PromptBuildError` for the one affected request,
deliberately **not** a module-scope raise: that would take every instance down at import
over one missing dict entry, killing generations of the types that work.

**What is specified but not built.** Topic hardening — the delimiting, the length cap on
the hydration path, NFC normalization, and the line-break handling that keeps a
multi-line topic from forging an instruction line — is designed (guards G19–G28) and
unimplemented. Until it lands, a `topic` is interpolated raw.

## Open

Two separate hand judgements, deliberately split — the premortem over commit `9c004c94`
caught that one checkbox was carrying both, and that the two are **anti**-correlated: a
реферат that volunteers a список литературы is *more* distinguishable from a доклад, so a
reviewer working the distinguishability item alone ticks it and never looks for
fabricated sources. Nothing in the automated suite can settle either one — the stub
returns a fixture regardless of the prompt.

- [ ] The реферат and доклад outputs are distinguishable to a reader. Judge one real
  generation of each by hand.
- [ ] The generated реферат carries **no** список литературы, no источники section and no
  numbered source entries. This is the item scenario 1.2's whole purpose rests on: the
  ban is an instruction to a third-party model, and no test in this repo can prove the
  model obeyed it. Judge one real generation by hand, looking specifically for invented
  sources — the failure mode is a plausible-looking bibliography with ISBNs that do not
  exist, in a document a student may submit for a grade.

## Load / Infrastructure

Both `n/a`, with the reasoning written in `tests/03_Load_Tests.md` and
`tests/04_Infrastructure_Tests.md` rather than left as a blank column.
