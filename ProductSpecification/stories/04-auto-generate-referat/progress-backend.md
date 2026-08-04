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

  **Corrected 2026-08-04** after the review passes over `9c004c94` — see the ADR's
  "Corrections" section. Four claims in the first revision were false (the Option B
  rejection mechanism, G10's field surface, G13's homoglyph rationale, and an unreconciled
  contradiction about unknown-type reachability), and the scoping was an accident rather
  than a judgement. Two things changed that `red-usecase` must build against, not just
  read past:
  - **The ban applies to all four types**, not реферат alone. Decided against the
    premortem's Incident 1: эссе and сочинение route to `_plain`, the API accepts them
    today (Security 3.1 pins that open on purpose), and an invented bibliography harms a
    student in an эссе exactly as much as in a реферат. `TYPES_REQUIRING_SOURCE_BAN`
    **equals** `SUPPORTED_DOCUMENT_TYPES` so a fifth type cannot arrive outside it.
    доклад is excluded through `_BAN_DEFERRED` — a scheduling freeze for story 1, guarded
    by G6's golden, not a judgement about доклад.
  - **G10 and G12 were rewritten to be runnable.** G10 now asserts the реферат template's
    fixed overhead in UTF-8 bytes against a named constant (writable against today's
    two-field `PromptRequest`); the at-caps half moves to 1.6, which is the scenario that
    adds the fields. G12 asserts over the derived set rather than a hand-listed one.

  The ban sentence is pinned in the ADR's Model section — G11 asserts its position and
  G13 its character class, and neither is writable against an unquoted string.
- [x] red-usecase — `backend/domain/tests/generation/test_referat_prompt.py`, class
  `TestAReferatPromptForbidsABibliography`, 7 methods (5 written, 2 added by
  `/test-review`). Predicted and actual failures matched on all five originals —
  AssertionError on the last line, AssertionError `342 == 446` on the byte overhead,
  `ValueError: substring not found` on the position guard, and `ImportError: cannot
  import name '_BAN_DEFERRED'` on the two derived-set guards.
  `TYPES_REQUIRING_SOURCE_BAN` / `_BAN_DEFERRED` are imported **inside** `_ban_scope()`,
  not at module scope: a module-level import of a not-yet-existing name is a *collection*
  error, which no skip marker can silence, so it would have reddened scenario 1.1's three
  passing tests for the duration of this RED.
  Two fail-opens `/test-review` closed are worth carrying into green:
  - `_BAN_DEFERRED` was subtracted but never asserted, so a `_BAN_DEFERRED` grown to cover
    everything left both iterating tests looping an empty list — green with the ban
    shipped nowhere. Both operands are now pinned by their own test, and the equality is
    `tuple(...) == SUPPORTED_DOCUMENT_TYPES` rather than `set(...) == set(...)`, which
    passed on a reordering or a duplicate, i.e. on a hand-maintained list again.
  - G6's доклад golden is scenario 1.3's, and 1.3 is unstarted — so the ADR's deliberate
    G12/G6 tension had only one side. `test_should_leave_the_deferred_type_s_prompt_free_of_the_ban`
    is the other side, in the file that owns the scope.
  One cross-check: the ADR's Edge Cases row for an empty `topic` (`PromptBuildError`)
  contradicts G10's own "with `topic` empty" wording, which would have made the overhead
  test unwritable. Built with a one-character probe topic and its UTF-8 length subtracted
  back out — same 446-byte constant, valid under either reading.
- [x] green-usecase — `TYPES_REQUIRING_SOURCE_BAN = SUPPORTED_DOCUMENT_TYPES` (a derivation,
  not a hand-listed tuple), `_BAN_DEFERRED = (DOKLAD,)`, and `BAN_SENTENCE` appended as its
  own last line in `build_prompt` rather than inside each template. Appending centrally is
  what makes the scope actually derived: a fifth long-form type joins
  `SUPPORTED_DOCUMENT_TYPES` and carries the ban with no human step, which is the hazard
  G12 exists to close. Per-template appends would have re-created the hand-maintained list
  one level down. `_referat` and `_plain` are untouched, so 1.3's goldens land on the
  pre-change text plus the ban line. 187 passed, 0 skipped.

  Coverage on the touched file: 21 statements, 0 missed, 2 branches, 0 partial — **100%**.
  `build_prompt`'s `if` is the file's only instrumented branch point and both arms are
  asserted (реферат/эссе/сочинение true, доклад false).

  **This is a deviation from the recorded design**, and it is deliberate rather than
  drift. The `design` step above chose Option A (the ban inside `_referat` only) and
  rejected Option B (a shared constant appended by `build_prompt` for every type). What
  landed is neither: a central append **gated by the derived set**. Option A's rejection
  of B rested on a claim the 2026-08-04 ADR correction had already found false — a global
  append would redden 1.3's доклад golden, except 1.3 is unstarted and the only доклад
  golden today is on `GigaChatProvider`'s own f-string. And the same correction's widening
  to all four types is what makes per-template emission the weaker option. The ADR's Model
  section ("its own sentence on its own line, last") is a statement about the built prompt
  and does not name the emission site; the Option A/B rows still do, and need reconciling
  along with the Edge Cases row flagged below.

  Two notes for scenario 2.1: `_requires_ban`'s first clause
  (`document_type in TYPES_REQUIRING_SOURCE_BAN`) is a tautology at its only call site —
  `build_prompt` subscripts `_TEMPLATES` first, so an out-of-set type raises `KeyError`
  before the predicate runs — and it is kept only because deleting it would leave
  `TYPES_REQUIRING_SOURCE_BAN` read by nothing. When доклад leaves `_BAN_DEFERRED` after
  story 1 lands, `_requires_ban` degenerates to `True` and the conditional can go entirely.
- [x] adapters-discovery — all three checks resolved `[S]`; no `red-adapter` /
  `green-adapter` step inserted. Re-run from scratch rather than inherited from 1.1,
  because this scenario did change `build_prompt`'s output.
  - Check 1 (ports): none. The unit is still `build_prompt` — a pure function over a
    `PromptRequest`, no constructor, no injected port, so there is no outbound adapter
    and no write-here-read-there flow. This scenario added three module constants and a
    conditional append; it persists nothing and enqueues nothing.
  - Check 1, the deliberate non-gap, restated because it is now sharper than it was at
    1.1: `grep -rn "build_prompt\|BAN_SENTENCE" backend/ acceptance/` returns **nothing
    outside `backend/domain/`**. `GigaChatProvider.generate` still composes its own
    f-string (`gigachat_provider.py:113-116`), so no реферат generation in production
    carries the ban this scenario just shipped. That is scenario 2.1's substitution to
    make; doing it here would leave 2.1 with a green adapter and nothing to redden.
    The premortem over `f5ae0842` is right that every artifact around this checkbox reads
    as though the ban ships today — that is a reporting hazard, not an adapter one, and
    the guard it names (a provider-level test asserting `BAN_SENTENCE` in the posted
    payload for a **реферат**) belongs to 2.1. Recorded there rather than opened here.
  - Check 2 (exceptions): none new. `build_prompt` still raises no domain exception.
    `_requires_ban` is a pure boolean and adds no failure mode; the only way out remains
    a `KeyError` on a type absent from `_TEMPLATES`, which the import-time assertion
    keeps unreachable. `PromptBuildError` does not exist yet — 1.4 / 3.3 own it.
  - Check 3 (response shape): `[S]`. Unchanged and re-checked from the adapter side: no
    endpoint returns the prompt, so no inbound response shape moves. `generation_router.py`
    returns `generation_id`/`status`/`created_at` plus echoed request fields, and Security
    scenario 2.1 requires the prompt stay out of even the log.
- [S] green-acceptance — nothing to turn green; see `red-acceptance` above.

### Scenario 1.3: A доклад prompt is unchanged by the move into the domain
- [S] red-acceptance — no acceptance surface, re-checked rather than inherited from 1.1
  and 1.2. This scenario is a golden `==` on the built prompt, which is the *least*
  black-box-observable assertion in the story: an equality on a string no endpoint
  returns and no log may contain (Security 2.1). Both halves re-verified today —
  `grep -rln prompt acceptance/` still returns only three *frontend* statement files
  (`chat_workspace_statements.py`, `composer_assertions.py`,
  `generate_flow_statements.py`, all UI placeholder copy, not the generation prompt),
  and `acceptance/conftest.py`'s fixture list still has no provider stub, so the
  outbound side is unobservable too.
  One distinction worth stating, because it is the tempting shortcut here: this
  scenario's golden text *is* reachable from a test — but through
  `GigaChatProvider`'s own f-string, in
  `backend/adapters/generation_provider/tests/provider/test_gigachat_provider_generate.py:51`,
  which is an adapter test, not an acceptance one, and which asserts the pre-story text
  the provider still composes. That test is 2.1's to move, not this scenario's to
  reinterpret as its acceptance surface. Covered by `red-usecase` / `green-usecase`.
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
