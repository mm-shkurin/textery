# Story 4: Auto-generate: реферат — Backend Progress

Owns Backend, Integration, Security, Load and Infrastructure Scenarios (acceptance steps
inline per scenario). Narrative and decisions live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

Scenario 1.1 starts the story because the prompt builder is a pure domain component: it
needs no adapter, no database and no stub, so the first work unit is the smallest one
that can be red.

## Backend Scenarios (tests/01_API_Tests.md)

### Scenario 1.1: A реферат prompt asks for the реферат structure
- [S] red-acceptance — the prompt has no black-box surface. The acceptance layer is
  HTTP-only with no compile dependency on `backend/` (no file under `acceptance/`
  imports it). No endpoint returns the prompt: `POST /api/v1/generations` returns
  `generation_id`/`status`/`created_at` plus echoed request fields, `GET
  /api/v1/generations/{id}` returns status and content — and Security scenario 2.1 of
  this same story requires the prompt not be written verbatim even to the log. The
  outbound side is no better: the DSL table's GigaChat stub server does not exist
  (`acceptance/conftest.py` has no provider-stub fixture; `gigachat_provider.py` posts
  to a module-level `COMPLETIONS_URL` on the live Sber host). The spec's own DSL settles
  it — "the prompt is built for it" is a direct in-process call on a pure domain
  component. Covered by `red-usecase` / `green-usecase` below.
- [x] design — ADR `decisions/prompt-builder-decision.md`, revised after the
  design-preview hazard scan (groups 1–8 dispatched; 8 dismissed as out of altitude).
  Nine in-scope GAPs folded in as named forced guards G1–G9; six pipeline-altitude
  findings recorded and mapped to the scenarios that own them.
- [x] red-usecase — `backend/domain/tests/generation/test_referat_prompt.py` (pure
  domain module, so the test lives in `domain/tests`, not `usecase/tests`).
  `PromptRequest` carries only `document_type` and `topic` so far — the ADR's other
  three fields arrive with the scenarios that read them (1.2–1.6, G2/G3), rather than
  sitting unreferenced. `/test-review` scoped each obligation to the sentence raising
  its section, so "введение **with** актуальность и цель" is a real assertion; the
  tightened fragments (`актуальность темы`, `цель работы`, `разделы по теме`,
  `выводы`, `во введении`/`в заключении`, topic interpolated) are now the
  specification green must satisfy. Substring checks by design — the golden `==` is
  scenario 1.3's job (G6).
- [x] green-usecase — `prompt_template.py`: `_referat` builder, `_plain` placeholder
  shared by the other three types, `_TEMPLATES` dispatch, import-time assertion against
  `SUPPORTED_DOCUMENT_TYPES`. 180 domain / 702 backend passed, 0 failed; the доклад
  adapter golden stayed green because `GigaChatProvider` was not touched. `_plain` is
  **not** byte-identical to today's provider f-string — that string interpolates
  `volume_pages`, and `PromptRequest` has no such field yet. Scenario 1.3 must add the
  field before its golden can land.
- [x] adapters-discovery — all three checks resolved `[S]`; no `red-adapter` /
  `green-adapter` step inserted.
  - Check 1 (ports): none. The scenario's unit is `build_prompt` in
    `backend/domain/src/generation/prompt_template.py` — a pure function taking a
    `PromptRequest` and returning a string. It has no constructor and no injected
    port, so there is no outbound adapter to find, and no write-here-read-there
    flow to reproduce. `RequestGeneration`'s two ports (`GenerationStorage`,
    `GenerationQueue`) are untouched by this scenario: it adds no field to
    `Generation` and changes nothing that is persisted or enqueued.
  - Check 1, deliberate non-gap: `GigaChatProvider.generate` still composes its own
    f-string prompt and does **not** call `build_prompt`, so a real реферат
    generation today still gets the доклад-shaped wording. That is not an
    insufficiency this scenario may fix — Scenario 2.1 ("The provider sends the
    prompt it was given") owns the substitution, and doing it here would leave 2.1
    with a green adapter and nothing to redden. Recorded rather than left implicit
    so the gap is not read as an oversight.
  - Check 2 (exceptions): none new. `build_prompt` raises no domain exception; the
    only failure mode is a `KeyError` on a document type absent from `_TEMPLATES`,
    and the module's import-time assertion against `SUPPORTED_DOCUMENT_TYPES` makes
    that unreachable at runtime rather than something the REST error handler must
    map. Rejection of an unsupported type happens earlier, in `Generation.create`,
    and is already mapped — Scenario 3.3 is its test.
  - Check 3 (response shape): `[S]`. No endpoint returns the prompt, so no inbound
    adapter response shape moves. This is the same finding that made
    `red-acceptance` `[S]` above, re-checked from the adapter side rather than
    assumed from it: `generation_router.py` returns `generation_id`/`status`/
    `created_at` plus echoed request fields, and Security scenario 2.1 requires the
    prompt stay out of even the log.
- [S] green-acceptance — nothing to turn green; see `red-acceptance` above.

### Scenario 1.2: A реферат prompt forbids a bibliography
- [S] red-acceptance — no acceptance surface, for the reason scenario 1.1 records at
  length: the DSL's "when the prompt is built for it" is an in-process call on a pure
  domain function, and nothing black-box can see the result. Re-checked rather than
  inherited — `grep -rl prompt acceptance/` still returns only three *frontend*
  statement files (UI placeholder copy, not the generation prompt), and
  `acceptance/conftest.py` still has no provider-stub fixture, so neither the inbound
  nor the outbound side of the prompt is observable over HTTP. This scenario adds one
  negative instruction to the same string, which changes nothing about that.
  Covered by `red-usecase` / `green-usecase` below.
- [x] design — Option A (one negative sentence inside `_referat` only), recorded by
  revising the existing ADR `decisions/prompt-builder-decision.md` rather than opening a
  second one: it already governs 1.1–1.6. Option B (a shared ban constant appended by
  `build_prompt` for every type) was rejected — scenario 1.3 pins a golden `==` on the
  доклад prompt as byte-identical to the pre-story `GigaChatProvider` f-string, and a
  global append would redden it while story 1 is being finished elsewhere against that
  exact output. All eight hazard groups re-dispatched from scratch (group 2 clear, group
  8 re-derived and dismissed as a block, groups 1/3/4/5/6/7 fired). Four in-scope GAPs
  folded in as G10–G13, G5 widened; six pipeline-altitude findings recorded and mapped.
  The one worth reading before `red-usecase`: **G2 is disjunctive** ("the ceiling holds
  *or* `PromptBuildError`"), so it is satisfied either way and cannot go red when
  реферат flips from one to the other — G10 is the non-disjunctive half, and it is this
  scenario's to carry because this is the change that grows `_referat`.
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: A доклад prompt is unchanged by the move into the domain
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4: Every supported document type yields a prompt
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5: The topic cannot displace the template's instructions
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6: Requirements and extra wishes cannot displace the instructions either
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: The provider sends the prompt it was given
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A реферат request is accepted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A реферат generation completes end to end
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: An unsupported document type is still rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: A duplicate submission does not generate twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (tests/06_Integration_Tests.md)

### Scenario 1.1: The реферат prompt reaches the provider
- [ ] red-integration
- [ ] green-integration

### Scenario 1.2: The provider's document becomes the generation's content
- [ ] red-integration
- [ ] green-integration

### Scenario 2.1: A provider error still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

### Scenario 2.2: A provider timeout still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

### Scenario 2.3: A malformed provider body still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

## Security Scenarios (tests/05_Security_Tests.md)

### Scenario 1.1: A hostile topic does not take over the generation
- [ ] red-security
- [ ] green-security

### Scenario 1.2: Every user-controlled field is treated as data
- [ ] red-security
- [ ] green-security

### Scenario 2.1: The prompt is not written to the log verbatim
- [ ] red-security
- [ ] green-security

### Scenario 2.2: A provider failure does not leak its raw body
- [ ] red-security
- [ ] green-security

### Scenario 3.1: A disabled card does not close the API
- [ ] red-security
- [ ] green-security

## Load Scenarios

- [S] n/a — the story exercises no operation belonging to the project's Throughput
  profile that story 1 does not already cover. Reasoning in `tests/03_Load_Tests.md`.

## Infrastructure Scenarios

- [S] n/a — no new service, container, connection, environment variable or migration;
  the moved prompt builder performs no I/O. Reasoning in
  `tests/04_Infrastructure_Tests.md`.
