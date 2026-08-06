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
- [x] design — Option A, recorded by revising the existing ADR
  `decisions/prompt-builder-decision.md` (it already governs 1.1–1.6) rather than opening
  a second one. All eight hazard groups re-dispatched from scratch; group 3 dismissed as a
  block (a pure deterministic builder has no shared state, no persistence, no read path).
  Seventeen GAPs collapsed to seven distinct guards across the seams.

  **The design.** `PromptRequest` gains `volume_pages`, `_plain` gains the
  ` ({volume_pages} стр.)` clause and so becomes byte-identical to the provider's
  f-string, and golden `==` lands for all four types (G6), not доклад alone: доклад bare,
  эссе/сочинение/реферат with `"\n" + BAN_SENTENCE`.

  Two alternatives rejected. Goldening доклад only contradicts G6 and the ADR's own
  "asserted lossless for every type, not asserted for one and assumed for the rest".
  Goldening доклад against the volume-less text and letting 2.1 reconcile does not assert
  the scenario's sentence — "exactly the text the provider composed before this story" —
  and would leave 2.1 free to drop the page count with nothing going red.

  **The decision the scan forced.** `volume_pages` is `int | None` end to end
  (`generation_request_dto.py` defaults it to `None`; `Generation.__init__`, the hydration
  path, applies no range check — only `create` does), and this is the change that makes it
  *render*. Five of eight groups independently flagged the same hazard: `_plain` emitting
  `доклад на тему: X (None стр.)` / `(0 стр.)` / `(-3 стр.)` to a billed third-party model.
  Decided to guard it here rather than defer to 1.6 — 1.3 puts the field on the object, so
  1.3 owns it. This is what finally puts `PromptBuildError` in the code; the ADR has
  specified it since 2026-08-01 and `grep` has never found it. **Scope limit**: 1.3 raises
  it and does not map it at the call site. That mapping is G5's, and `build_prompt` still
  has no caller until 2.1.

  **Guards `red-usecase` must carry**, beyond the four goldens:
  - **G3** — `volume_pages` `None` / `0` / negative / above `MAX_VOLUME_PAGES` →
    `PromptBuildError`, asserted for a `_plain` type, not only for реферат. Subsumes the
    injection hazard group 5 raised on the same field: an enforced `int` cannot carry a
    newline, so no forged instruction line is reachable through it.
  - **G9** — `build_prompt(r) == build_prompt(r)` and `r` unmutated, all four types. A
    golden asserts the first call only, so a builder that memoized into a mutated buffer,
    or normalized `document_type` in place, passes every golden while the retry's second
    attempt sends a different string than its first.
  - **G4** — `topic` `None` / empty / whitespace-only → `PromptBuildError`. Added after
    the review passes over `db5113d8`, which caught that the owner sweep assigned G3 and
    missed G4 while the argument for G4 is stronger: `_plain` has interpolated `topic`
    since 1.1, so `на тему: None` is reachable today.
  - **G15** — `_plain`'s fixed overhead in UTF-8 bytes against a named constant. G10
    covers `_referat`, the one template this scenario does not change.
  - **G16** — `PromptRequest.__init__`'s accepted parameter set is exactly the three
    names. Its narrowness is the entire reason the "method on `Generation`" option was
    rejected, and adding `owner_id` today turns no test red. 1.6 grows the field set
    again, so the ratchet has to exist before then.
  - **G13** — restated as per-type, matching G6's scope. This scenario goldens `на тему:`
    and `стр.` for the first time, and three of the five homoglyph-bearing characters
    appear in those two fragments.

  **Corrected in the ADR**, because a 1.3 author reading it would have been misled into
  reverting the ban: the Edge Cases row promising эссе/сочинение goldens byte-identical to
  the pre-change f-string (false since the 2026-08-04 ban widening — and the cheapest fix
  for the resulting red, adding them to `_BAN_DEFERRED`, silently unbans half the types
  that need it); the Rejected/Chosen rows still placing the ban inside `_referat`; and the
  ADR's `PromptRequest` bullet, which now names which scenario each field arrives with.
  `_plain`'s docstring carries a third copy of the same stale claim — that one is a source
  change and belongs to `green-usecase`.

  **Corrected after the review passes over `db5113d8`**, before `red-usecase` could build
  against any of it:
  - **G14 does not belong to `red-usecase` and is not per-type.** It drives
    `GigaChatProvider`, so it is an adapter test under
    `backend/adapters/generation_provider/tests/` — a domain or usecase test importing an
    adapter inverts the dependency rule, and it would resolve at runtime anyway because
    `backend/pyproject.toml` puts every layer root on one `pythonpath`, so the violation
    lands silently. And it is assertable for **доклад alone**: the provider appends no
    ban, `build_prompt` appends one for every type outside `_BAN_DEFERRED`, so
    parameterizing it like G6/G13 is red on arrival for the other three with no defect
    present — and the cheapest escape from that red is to widen `_BAN_DEFERRED`, which
    unbans them. That escape is already blocked by `test_referat_prompt.py:227`, but the
    scope note keeps an author from reaching for it and backing it out.
  - **G15's terms had to be stated**, because G10's do not transfer. `_referat` hardcodes
    its type name so it has one fixed overhead; `_plain` interpolates `document_type`
    (12 / 8 / 18 bytes) and `volume_pages` (1–2 digits), so there is no single constant.
    Assert `len(built) - len(document_type) - len(str(volume_pages))` against one constant
    covering all three types. Pinning one type at one volume is the cheap exit that made
    G10's first formulation unwritable.
  - **`red-usecase` must update the existing tests, and no step said so.**
    `test_referat_prompt.py:51` is the single `PromptRequest(document_type=..., topic=...)`
    call site that all seven 1.1/1.2 tests route through. A required `volume_pages` makes
    it a `TypeError`; an optional one defaulting to `None` makes G3 raise for every one of
    them. Either way the RED phase edits a green test file — worth naming, given how
    carefully that file's own comments were written to avoid reddening 1.1.
  - **`PromptBuildError`'s base class is now pinned in the ADR** rather than left to the
    implementation. Deferring the call-site *mapping* to G5/2.1 does not defer the
    *default*: `generate_document.py:61` catches bare `Exception` and retries, so an
    unmapped build failure is retried as if transient — deterministic, so attempt 2 burns
    the budget for nothing.
  - Two smaller corrections: the ADR revision table's own second row was false (it sent
    the reader to fix two sections that never said what it claimed), and G13's rationale
    said three homoglyph-bearing characters appear in the newly-goldened fragments when it
    is four.

  **Routed elsewhere, not folded in**: G17 (the import-time `_TEMPLATES` completeness
  check is a bare `assert`, which `python -O` strips, so the fifth-type guard holds by
  accident of interpreter invocation) → **1.4**, whose sentence it is. Log disclosure of
  `topic` through the error path → Security 2.1 / 2.2, already recorded. Migration
  `d0e1f2a3b4c5`'s unfiltered bulk rewrite still has no owning scenario and needs a task.
- [x] red-usecase — `TestADokladPromptIsUnchangedByTheMoveIntoTheDomain`, 49 cases
  (33 written, grown to 49 by `/test-review`). 41 red / 8 green when the skip marker is
  stripped; 187 domain passed, 49 skipped, 0 failed with it on; ruff clean. Predictions
  matched on all 33 originals — `AssertionError` on the goldens missing ` (5 стр.)`,
  `ImportError: cannot import name 'PromptBuildError'` on the G3/G4 cases, and
  `AssertionError: _plain fixed overhead moved, got 14 bytes … assert 14 == 27` on G15.
  The доклад adapter golden stayed green; `GigaChatProvider` was not touched.

  **One line of production code landed during RED**, and it is the sanctioned kind:
  `PromptRequest.__init__` gained `volume_pages: int` and its assignment, nothing else —
  no volume clause in `_plain`, no validation, no `PromptBuildError`. Without it the
  shared helper's third argument is a `TypeError` and all ten existing 1.1/1.2 tests go
  red for the duration of this phase. `tdd-rules.md` names a new field on a request DTO as
  allowed plumbing.

  **Four things `/test-review` caught that would have shipped a guard asserting nothing:**
  - **G15 was blind to its own hazard.** Measuring `splitlines()[0]` isolates the ban
    correctly but also discards any second line `_plain` itself grows — and "a sentence
    added to `_plain`" is the entire reason G15 exists. It would have sat at 27 bytes
    while the template doubled. Now measures the whole prompt and subtracts a
    `BAN_LINE_BYTES` derived from the already-pinned `BAN_SENTENCE` rather than hand-typed.
  - **G16 had an unfirable assertion.** `leaked = [n for n in FORBIDDEN_GENERATION_FIELDS
    if n in accepted]` runs after the line pinning `accepted` to exactly three names, so it
    could never be non-empty. Worse, a signature says nothing about *instance attributes* —
    an `__init__` taking the three declared parameters can still assign `self.owner_id`,
    which passes every assertion while putting a server-owned field one attribute access
    from a template. Split into a structural `(name, kind)` comparison and an
    attribute-tuple assertion, with `FORBIDDEN_GENERATION_FIELDS` itself pinned against
    `Generation.__init__`'s real signature — a rename on the entity would otherwise have
    emptied the guard silently.
  - **G9 was relative.** `second == first` passes for a builder that memoizes the *wrong*
    string. Both calls now pin to `GOLDEN_PROMPTS[document_type]`, which turned the three
    `_plain` types red and asserts *which* string is repeated. Added the half of G9 the ADR
    states and the first draft omitted: `_TEMPLATES` compared by key **and callable
    identity**, and a `deepcopy` baseline for the mutation check — a shallow copy compares
    equal after an in-place field mutation, latent today and live once 1.6 adds two fields.
  - **14 bare `pytest.raises` were existence-only.** `PromptBuildError` is a family, so
    raising `UnsupportedDocumentTypeError` for `volume_pages=-3` passed. Now
    `type(exc) is PromptBuildError` plus `str(exc) ==` a named constant. Both messages were
    decided here rather than deferred: they name the field and carry **no interpolation
    slot**, which is structurally what keeps the user's `topic` out of the log line
    `generate_document.py:69-75` writes. A new test pins `PromptBuildError`'s base class,
    which the ADR assigns to this scenario and nothing asserted.

  Eight cases are green and stay green: the four Cyrillic (G13) and two G16 ratchets are
  behaviour-pinning by nature, and реферат's golden and determinism cases pass because
  `_referat` interpolates no volume — which is precisely the claim G6 makes about the one
  template this scenario leaves alone.

  **G14 is deliberately absent from this file.** It drives `GigaChatProvider`, so a domain
  test carrying it would invert the dependency rule — and would resolve at runtime anyway,
  since every layer root shares one `pythonpath`. It belongs to an adapter test and will
  arrive as a discovered step at `adapters-discovery`.
- [x] green-usecase — `prompt_template.py` (146 lines): `PromptBuildError(DomainException)`,
  the two no-interpolation-slot message constants, `_reject_unrenderable_fields(request)`
  called at the top of `build_prompt`, and the ` ({volume_pages} стр.)` clause on both
  `_plain` and `_referat`. 68 passed in the scenario file (was 52 failing), 245 domain,
  767 passed / 2 skipped across `pytest backend/` — the 2 are pre-existing
  optional-dependency skips (`htmldocx`, `weasyprint`) in the rendering adapter. Coverage
  on the touched file: 39/39 lines, 8/8 branches.

  **The guard sits in `build_prompt`, not `PromptRequest.__init__`** — the ADR does not
  say which, but the test's `_prompt_request` helper constructs requests with bad values
  and expects the raise from the build call, so `__init__` was never available. It runs
  *before* the `_TEMPLATES` dispatch so it covers every type, not only the templates that
  interpolate the field.

  **Three things the ADR leaves open, decided here.** Volume is checked before topic
  (unobservable — no test violates both — so it follows the Edge Cases table's order).
  Both guards are type-and-value (`isinstance` plus range) rather than value-only, which
  is what makes `None` fall out without its own branch, but also rejects a `"5"` volume
  the ADR never rules on. And `bool` is excluded from the volume type, which the ADR's
  Edge Cases row does not mention — see the coverage steps below.

  **`--focus` returned no files and had to be overridden.** The pathspecs in
  `.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:38,44` do not
  match `backend/domain/src/generation/prompt_template.py`; they will silently return
  empty for every nested-package file in this repo. Needs a task.
- [x] red-usecase (coverage: volume_pages of True is rejected, not rendered) — 100%
  branch coverage is misleading on `_is_renderable_volume`: branch counters record
  whether the `if` was taken, not which operand decided it. `None` short-circuits on the
  left, `0`/`-3`/`11` reach `isinstance(volume_pages, bool)` and it always answers
  `False`, so no test ever lets that operand decide. Deleting it leaves 68 passing — the
  mutant survives. It is reachable, not defensive: `MIN_VOLUME_PAGES = 1` and `True == 1`,
  so without the guard a prompt reads `... (True стр.)` — a Latin-lettered artifact billed
  to the model. (The coverage pass proposed adding `True` to `UNRENDERABLE_VOLUMES` — see
  the next paragraph for why that was rejected. Its pointer `test_referat_prompt.py:127`
  had also gone stale in the 9ed69580 split; the tuple now lives in
  `test_prompt_build_refusals.py`.)

  **Written as its own test, not as a fifth entry in `UNRENDERABLE_VOLUMES`.** `True` is
  the only unrenderable volume that is *inside* the accepted range; the other four are
  refused by the comparison. Sitting beside `-3` it reads as another out-of-range value,
  and the next reader deletes the `isinstance(..., bool)` arm as redundant — which is the
  mutant. `test_should_refuse_a_boolean_volume_the_range_check_cannot_catch` in
  `test_prompt_build_refusals.py`, parametrized over all four types. 4 passed; 4 failed
  with `Failed: DID NOT RAISE PromptBuildError` when the operand is deleted, which is the
  real red here. 90 passed in the generation suite.

  **`/test-review` found the first draft asserted the raise but not the harm.** The
  comment named `(True стр.)` reaching a prompt and then checked only that an exception
  came out. It now also builds at the numeric twin (`int(True)` is 1) and pins
  `twin_prompt.count("(1 стр.)") == 1` — `count`, not `in`, so a duplicated clause cannot
  pass. That build replaced a `MIN_VOLUME_PAGES <= True <= MAX_VOLUME_PAGES` precondition
  which restated two constants and ran no production code. Three more: the obsolete
  `_prompt_build_error()` deferred-import helper is gone (`PromptBuildError` exists now,
  so its justification had become false); `prompt_request`/`prompt_for` widened
  `str`/`int` → `object`, since `volume_pages: int` asserted the opposite of what this
  test proves (mypy counts `bool` as `int`) and `None` is not an `int` at all — the lie
  survived only because parametrize launders values through an untyped param; and the
  message constants stay retyped rather than imported, because importing them would make
  three assertions tautologies that pass for any message, including one that grew an
  interpolation slot and logged the user's `topic`.
- [S] green-usecase (coverage: volume_pages of True is rejected, not rendered) — nothing
  to implement. The guard shipped with 1.3's GREEN; the gap was that no test let its
  `bool` operand decide the outcome. The step exists because branch coverage cannot see
  the difference.
- [x] adapters-discovery — Check 1 produces one pair (G14); Checks 2 and 3 resolve `[S]`.
  Re-run from scratch rather than inherited from 1.2, because this scenario changed
  `build_prompt`'s output for all four types and added its first raise.
  - Check 1 (ports): `generation_provider` — **G14, the assertion the ADR routed here at
    1.3's red-usecase**. `build_prompt` itself is still a pure function with no injected
    port, so this is not an outbound-port gap in the usual sense; it is the second live
    composer. `GigaChatProvider.generate` builds its own f-string at
    `gigachat_provider.py:113-116`, and after this scenario the two definitions of the
    доклад prompt agree byte-for-byte — which is precisely the claim "unchanged by the
    move" makes and precisely what nothing asserts. Each is pinned only by its own golden,
    so either can be edited alone with nothing red. Golden-vs-golden cannot force the
    agreement; only an assertion whose two sides are the two composers can. Steps
    inserted below; scoped to доклад alone per the ADR (the provider appends no ban, so
    parameterizing over `SUPPORTED_DOCUMENT_TYPES` is red on arrival for the other three
    with no defect present, and the cheapest escape from that red is to unban them).
  - Check 1, the deliberate non-gap, restated once more: `grep -rn "build_prompt" backend/
    acceptance/` still returns nothing outside `backend/domain/`. No production code calls
    the builder, so no реферат generation in production carries the ban or the refusals
    this scenario shipped. That substitution is 2.1's; making it here would leave 2.1 with
    a green adapter and nothing to redden.
  - Check 2 (exceptions): `[S]`. `PromptBuildError` is new and genuinely unmapped —
    `generate_document.py:59` catches bare `Exception` and retries, so a deterministic
    build failure would burn both attempts and a backoff sleep. But it is unreachable
    today for the reason Check 1 records: nothing outside the domain calls `build_prompt`,
    so no inbound adapter can see the exception. Mapping it now would be a guard against a
    call that does not exist. It becomes 2.1's obligation the moment the substitution
    lands, and both review passes over `7c840827` named it — recorded there, not opened
    here.
  - Check 3 (response shape): `[S]`. Unchanged and re-checked from the adapter side. No
    endpoint returns the prompt; `generation_router.py` returns
    `generation_id`/`status`/`created_at` plus echoed request fields, and Security 2.1
    requires the prompt stay out of even the log. This scenario's `red-acceptance` is `[S]`
    for the same reason, so there is no disabled test to read a shape from.
- [x] red-adapter generation_provider (G14: the two live composers agree on the доклад
  prompt) — `test_gigachat_provider_prompt_agreement.py` (85 lines). Drives
  `GigaChatProvider.generate` and asserts the posted `content` equals `build_prompt(...)`
  from the same `Generation`; both sides are live composers, no hand-typed literal. Home
  is the adapter: a domain or usecase test driving the provider inverts the dependency
  rule, and would resolve at runtime anyway because `backend/pyproject.toml` puts every
  layer root on one `pythonpath` — so the violation would land silently. 27 passed in the
  adapter suite, 276 across adapter + domain, 772 / 2 skipped across `pytest backend/`.

  **Predicted PASS, actual PASS.** The composers already agree for доклад, so the real
  red is a mutation red. Three mutations, each restored bit-for-bit: provider alone (extra
  space after `на тему:`) → `AssertionError`; domain alone (`на тему:` → `по теме:` in
  `_plain`) → `AssertionError`; and the decisive one — **the provider f-string edited
  together with its own golden**, which is exactly the edit G14 says is invisible today →
  `1 failed, 26 passed`, the sole failure being this test. Every pre-existing guard,
  including the provider's own golden, moved with the mutation and stayed green. The
  domain side was already somewhat pinned (mutation 2 also reddens `_plain`'s golden); the
  provider side was the genuinely open one.

  **`/test-review` found the assertion self-destructs at 2.1.** The moment the provider
  delegates to `build_prompt`, both sides of the `==` become the same call and the
  comparison is a tautology that passes forever covering nothing — with no test edit to
  notice. Verified: under a simulated 2.1 provider the agreement assertion goes green.
  Independence is now asserted by a second method that fails loudly with an instruction to
  **delete the file**, not to silence the guard — substitution is what makes G14
  structurally unnecessary, and that is the correct resolution, not a skip marker.

  Three more from the same pass. The доклад scope was riding on a shared
  `build_generation()` default that four other test files also use — any of them could
  legitimately retarget it and silently re-scope this assertion into a defect-free red
  whose cheapest escape is widening `_BAN_DEFERRED`; the scope is now executable
  (`build_doklad_generation()` asserts the type). The completions call was picked
  positionally (`_token_call, completions_call = ...`) with nothing pinning that call 2 is
  the completion; a `posted_completion_messages(client)` fixture now locates it by
  `COMPLETIONS_URL` and requires exactly one match, so "no completion posted" and "more
  than one" become named failures. And `messages[0]["content"]` was a shallow index — a
  prepended system message would give a misleading red, or a false green if it carried the
  доклад text; the whole `messages` list is now compared in one strict equality.

  **Two findings left for `/refactor`, deliberately**: `test_fake_provider.py:7` holds a
  verbatim duplicate of `build_generation` that would drift from the доклад scope
  unnoticed, and `test_gigachat_provider_generate.py:51`'s hand-typed golden is coupled to
  the fixture's topic/pages. Narrowing that golden would have *reduced* strictness, so
  `/test-review` correctly declined it.
- [S] green-adapter generation_provider (G14) — the prediction held, and it was checked
  rather than assumed. There is no disable marker in
  `test_gigachat_provider_prompt_agreement.py` to remove: the red landed the file enabled
  because its red was a mutation red, so GREEN had nothing to enable and nothing to
  implement. Both G14 methods pass on the untouched tree (2 passed), the adapter module is
  27 passed / 0 failed, and `pytest backend/` is 716 passed / 59 skipped / 0 failed.
  Writing the provider→`build_prompt` substitution here would have been the *wrong* green:
  that substitution is Scenario 2.1's behavior, and doing it now would leave 2.1 with a
  green adapter and nothing to redden.
  The skip count moved from the red run's `772 / 2` to `716 / 59` — environmental, not a
  regression: every extra skip is a `backend/adapters/db` integration test reporting
  `no database listening at localhost:5432` (Postgres was up during red, down now), plus
  the two pre-existing `htmldocx`/`weasyprint` optional-dependency skips. No
  `generation_provider`, domain or usecase test is skipped.
  `/test-coverage generation_provider --focus` confirmed the empty focus diff is correct
  rather than a broken filter (green wrote no code at all): adapter sits at 95/97
  statements (98%) and 8/8 branches (100%), 0 partial. The two uncovered statements are
  both older than this work unit and out of its scope — `fake_provider.py:26` (`aclose`'s
  `return None`, reachable from `application/src/app/container/runtime.py:23`, introduced
  `e5cd85ef`) and `gigachat_provider.py:167` (the `ProviderError` on the *token* handshake
  — `TestGenerateProviderError` covers the completions call, not the OAuth one; introduced
  `bbdcfdf9`). The latter has a natural owner already on the board, Integration Scenario
  2.1 "A provider error still ends the generation as failed"; no steps were pre-written
  under it. No steps were added to this scenario either — attributing foreign code to 1.3
  would be a false claim of coverage.
- [S] green-acceptance — follows `red-acceptance` `[S]`, but re-checked rather than
  waved through, because a green-acceptance step's only legitimate action is to remove a
  disable marker from a test the red phase left disabled: there is no such test.
  `grep -rln 'referat\|реферат' acceptance/` returns nothing at all, and no acceptance
  file names this scenario — the only `Scenario 1.3` hits under `acceptance/` belong to
  other stories (password policy, export format guard, the auth verify-code screen).
  One new piece of evidence, stronger than the red note's: the acceptance stack runs
  `GENERATION_PROVIDER=fake` (`acceptance/statements/frontend/generation/auto_editor_transition_expectations.py:35`),
  so `GigaChatProvider` — one of the two composers whose agreement this scenario asserts —
  is never wired into the acceptance process at all. The assertion is not merely hard to
  observe over HTTP; the object under test does not exist in that stack. `conftest.py`'s
  fixture list still contains no provider stub (its `provider_secret` fixture is the
  Yandex OAuth secret for the log-leak invariant, not a GigaChat stub).
  **Scenario 1.3 is now complete.**

### Scenario 1.4: Every supported document type yields a prompt
- [S] red-acceptance — decided on this scenario's own merits, not inherited from 1.1–1.3,
  because the spec's note names what looks like a black-box consequence: "a type without a
  template would raise inside the worker — after enqueue, consuming the retry budget,
  landing as `failed`". That consequence is **not reachable today, and not reachable by any
  HTTP input**:
  - **`build_prompt` has no production caller.** `grep -rn "build_prompt" backend/ acceptance/`
    outside `*/tests/*` returns exactly two hits, both in
    `backend/domain/src/generation/prompt_template.py` — its own `def` at line 134 and a
    docstring mention at line 85. Nothing in the worker path calls it, so nothing in the
    worker path can raise from a missing template.
  - **The acceptance stack's provider builds no prompt at all.** `GENERATION_PROVIDER=fake`
    selects `FakeProvider` (`container/runtime.py:22`), whose `generate` returns the
    constant `FAKE_DOKLAD_TEXT` and never touches `PromptRequest`. The premise that
    "prompt-building still happens in the worker" does not hold for `fake`. The other
    implementation, `GigaChatProvider`, still composes its own text — the substitution is
    2.1's obligation, as the ADR and scenario 1.3's `adapters-discovery` both record.
  - **Even after the substitution lands, no request can select a template-less type.** The
    two sets are the same set by construction: `_TEMPLATES` is keyed by
    `DOKLAD/ESSE/SOCHINENIE/REFERAT` and `prompt_template.py:98` asserts
    `set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)` at import. A type outside that tuple
    is rejected before enqueue by `Generation`'s own guard
    (`generation.py:26`, "document_type must be one of: …") — which is scenario **3.3**'s
    sentence, not this one. So the `failed` landing this scenario describes has no input
    that produces it: supported types always have a template, unsupported types never reach
    the worker.
  - **No endpoint enumerates the supported types.** The full router surface is auth, oauth,
    documents, generations, health — none of them returns
    `SUPPORTED_DOCUMENT_TYPES`, so "each document type the domain supports" cannot even be
    driven from a black-box client without hard-coding the tuple, which would pin a copy
    rather than the domain's own list.
  - The spec's own DSL settles it the same way it settled 1.1–1.3: "each document type the
    domain supports" → *"Parametrized over `SUPPORTED_DOCUMENT_TYPES`"*, and "the prompt is
    built for it" → a direct in-process call. Covered by `red-usecase` / `green-usecase`
    below, in `backend/domain/tests/generation/`.

  **Coverage is not lost to a neighbour** — the black-box halves of this territory are
  already owned: **3.2** ("a реферат generation completes end to end … records its type as
  реферат") owns "a request for a supported type produces content over HTTP", and **3.3**
  ("an unsupported document type is still rejected") owns the rejection. Writing an HTTP
  test here would be one of those two under a different name.

  **G17 stays with this scenario and needs a domain-layer step, not an acceptance one.**
  Routed here by 1.3: the completeness check at `prompt_template.py:98` is a bare `assert`,
  which `python -O` strips — so the fifth-type guard currently holds by accident of
  interpreter invocation. That is precisely this scenario's sentence, and it is testable
  only in-process. `design` should decide whether the check becomes an explicit raise at
  import or a test-only obligation.
- [S] green-acceptance — nothing to turn green; see `red-acceptance` above.
- [x] design — **Option D**, recorded by revising the existing ADR
  `decisions/prompt-builder-decision.md` (it already governs 1.1–1.6) rather than opening a
  second one. All eight hazard groups re-dispatched from scratch; group 8 dismissed as a
  block (no client surface, derived not assumed). Groups 1–7 fired, 21 GAPs.
  **The scan reversed this scenario's own inherited instruction.** G17, written by the 1.3
  scan and read as settled, mandated that the completeness check "fails at boot as a
  raised, named exception". Implementing it verbatim would have traded a missing dict
  entry for a fleet-wide outage: a module-scope raise means a deploy where
  `SUPPORTED_DOCUMENT_TYPES` gains a fifth type before `_TEMPLATES` does takes down every
  instance at import, killing generations of the four types that work. `ImportError` was
  additionally the wrong class — the one exception routinely swallowed by optional-import
  `try/except`, turning fail-closed into a silent skip. Option D keeps the pre-deploy catch
  the boot-raise was reaching for, but moves it into a test (which `-O` cannot strip) and
  makes the runtime failure a scoped `PromptBuildError` instead of a process crash.
  **G5 is the seam guard, it already existed, and it has never been implemented.** All
  seven live groups independently flagged "a `PromptBuildError` retried on a value that
  cannot change on attempt 2", each assuming another pass owned it. It is not a new guard —
  it is G5 from the 1.1 scan. `grep -rn PromptBuildError` outside `backend/domain/` still
  returns nothing. The new part is a placement obligation on 2.1: G5 asserts "provider
  called **zero** times", which presumes the build happens at the call site, so nesting
  `build_prompt` inside `GigaChatProvider.generate` would make G5 unsatisfiable as written
  and invite whoever meets the red to weaken it. Both obligations are named in the ADR.
  New guards folded in: **G17 restated**, **G18** (the per-type assertion must be
  type-discriminating, not truthiness — `assert built` is satisfied by a mojibake prompt,
  and the ban table has no per-type completeness assertion of its own).
  Seven pipeline-altitude findings recorded and mapped; four that fired again were left to
  their existing rows rather than duplicated.

  **Corrected the same day, after both review passes over `dd9b0f72` reached the same two
  holes independently.** The design as first committed was right about G17 and
  under-specified about what replaces it:
  - **G17(b) dropped the completeness claim rather than moving it.** A test that removes a
    template and asserts the refusal exercises the *refusal mechanism*; it is green whether
    `_TEMPLATES` covers `SUPPORTED_DOCUMENT_TYPES` or not, so the fifth-type hazard passes
    it unchanged. The deleted `assert` was a set **equality**, catching both directions.
    G17(b) now requires two tests, the second an explicit `set(_TEMPLATES) ==
    set(SUPPORTED_DOCUMENT_TYPES)`. Leaning on the parametrized suites to catch it
    incidentally is what G14's scoping already showed evaporates.
  - **G5 had no owner, and this scenario is the one removing the loud guard.** It is now
    assigned to 1.4's `red-usecase` / `green-usecase`. G5 has been re-flagged by seven
    hazard groups across three scans and never implemented, precisely because its row named
    nobody. Deleting the module `assert` while `PromptBuildError` is still swallowed by
    `generate_document.py`'s `except Exception` — retried on backoff, then surfaced as
    "попробуйте позже", advice that is false forever, at a severity shared with routine
    provider blips — is paying for the reversal on credit. **1.4 carries both halves or
    neither.**
  Also corrected: the 2.1 obligations said "2.1" unqualified where the story has three
  (Backend, Integration, Security) — they are **Backend 2.1**'s, and are now copied inline
  under that scenario's block rather than living only in the ADR; the "or at minimum before
  `gigachat_provider.py`'s `try`" fallback was withdrawn as self-contradictory (it sanctions
  the provider being called, which is exactly what G5 forbids); the NFC row cited
  `Email`/`Password` backwards (both cap *then* normalize, deliberately — `DocumentContent`
  is the right precedent, with its post-NFC re-cap) and is reassigned from unowned to
  **Backend 1.5**, whose spec the 1.2 scan already widens over the same surface; and G18's
  mojibake rationale was narrowed, since G13 already guards that half.

  Left genuinely unowned, and it is a note rather than a guard: the hydration path applies
  no `topic` length cap at all.
- [x] red-usecase — Option D's two halves landed together, as the design required.
  **Domain** (`test_prompt_type_coverage.py`, `test_prompt_type_refusal.py`): G17(b) as two
  tests, not one — the refusal (`PromptBuildError` for a type with no template, and for a
  supported type whose template was removed) *and* a separate explicit
  `set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)`, because a refusal-mechanism test is
  green whether the sets match or not. G18 as a type-discriminating assertion:
  `prompt.count(document_type) == 1` plus first-line placement, not `assert built`. The
  hand-declared `EXPECTED_BAN_SIDE` table is deliberately not derived — a derived table
  moves with the mutation and stays green.
  **Usecase** (`test_generation_prompt_failure_usecase.py` + three Statements files):
  **G5, implemented at last** — flagged by seven hazard groups across three scans, owned by
  nobody until this scenario. Asserts the provider is called **zero** times, no backoff was
  ever awaited, exactly two writes, and the offending row written back unaltered.
  Three guards pin existing behavior, so their real red is a **mutation red** (the G14
  precedent from 1.3). Each was verified to fire and production restored bit-for-bit:
  dispatch ignoring the requested type → 6 failed; `_BAN_DEFERRED = (REFERAT,)` → 4 failed;
  a stale `"диссертация"` template key → 3 failed — the last being the direction the ADR
  records as "caught by nothing today".
  `/test-review` widened eight findings. The load-bearing one: the row-unaltered assertion
  compared 3 of `Generation`'s 12 fields on 1 of 2 snapshots — `owner_id` and `version`
  were omitted, so a `fail()` on a rewritten owner (a lost update) or a bumped version (a
  broken CAS) passed. Now all 9 invariant fields on every snapshot, with a tripwire that
  fails loudly if a 13th field is added. Two module-scope `assert` premises were relocated:
  in the Statements an import-time failure there takes the **whole usecase suite's
  collection** down as an error rather than failing the test whose premise it is.
  Two findings were left to `/refactor` or to a global decision rather than fixed here:
  P-16 (storage port injected into Statements) is a real rule violation but repo-wide
  across 17 files, and this scenario is unwritable without it — it needs the
  `Generation.__init__` hydration path, which no usecase can produce; S-11 (duplication
  with `generation_lifecycle_statements.py`) needs a cross-file extraction outside this
  unit's diff.
  Counts: `pytest backend/` **783 passed, 6 skipped, 0 failed**; the four RED tests with
  their skip markers stripped, **4 failed** — both domain ones `KeyError` at
  `prompt_template.py:143`, both usecase ones
  `AssertionError: a prompt that cannot be built must reach no provider, got 1 call(s)`.
  `git diff` over `backend/*/src` is empty — no production code.
  **For green**: G5's two cases fail on the *first* assertion (the call count), so the four
  behind it are staged but not yet exercised. Green must re-run and confirm all five pass,
  not stop when the count reaches zero — a catch-all that slept once and gave up satisfies
  the count and still fails `assert_never_waited`.
- [x] green-usecase — Option D's two halves landed together, as the design required that
  they must. **Domain** (`prompt_template.py`, 159 lines): the module-scope
  `assert set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)` is gone, and `_select_template`
  raises `PromptBuildError(f"no prompt template for {document_type}")` in place of the bare
  `_TEMPLATES[...]` subscript. Nothing raises at module scope: that was the reversal 1.4's
  scan forced, because a boot-time raise trades a missing dict entry for a fleet-wide
  outage. The completeness claim now lives only in `test_prompt_type_coverage.py`, which
  `python -O` cannot strip — which is the whole point of moving it.
  **Usecase** (`generate_document.py`, 131 lines): `_compose_prompt(generation)` builds the
  `PromptRequest` and calls `build_prompt` **before the attempt loop**, and the
  `except PromptBuildError` sits ahead of `last_error` and the loop. A build failure logs at
  `error`, calls `generation.fail(GENERIC_FAILURE_MESSAGE)`, writes once, and returns — the
  `except Exception` retry path is never entered. That is **G5, shipped**: flagged by seven
  hazard groups across three scans and owned by nobody until this scenario.
  787 passed, 2 skipped, 0 failed across `pytest backend/` (was 783 / 6 — the four enabled
  tests account for the delta exactly); ruff clean. Only skip markers were removed from the
  tests, plus the `import pytest` that stripping the class-level marker orphaned.
  **All five G5 assertions were confirmed exercised, not just the first.** RED left them
  staged behind a failing call count, so green re-ran and watched
  `assert_the_build_failure_was_terminal_and_unbilled` run to completion on both arrival
  paths — the unsupported type through `_select_template`, the over-ceiling volume through
  `_reject_unrenderable_fields`. `assert_never_waited`, the `[get, update, update]`
  sequence, the exactly-two-writes/status pair and the nine-field unaltered-row check over
  both snapshots all passed, so a catch-all that slept once and gave up is genuinely
  excluded rather than merely un-contradicted.
  **The composed prompt is deliberately discarded.** `provider.generate(generation)` is
  untouched, so Backend 2.1 still has the substitution to redden — composing it here and
  handing it over would have left 2.1 with a green adapter. Placement honours 2.1's
  inherited obligation nonetheless: the build is at the call site, not inside
  `GigaChatProvider.generate`, which is what keeps G5's zero-call assertion satisfiable.

  Coverage: `prompt_template.py` 43/43 statements, 10/10 branches; `generate_document.py`
  54/54 statements, 6/6 branches — **100% both, 0 partial**, read line-by-line from
  `coverage.xml` rather than off the summary row. `--focus` was again overridden by hand,
  for the reason 1.3 recorded. Because 1.3 proved 100% can be misleading, the pass ran
  mutants at the four new decision points instead of trusting the counters: deleting
  `_select_template`'s raise → 3 failed; deleting the `return` after the terminal `fail()`
  so the row falls into the retry loop → 2 failed (G5 firing as designed); emptying the
  refusal message → 2 failed. 1.3's specific defect class does not recur — neither new
  decision point is compound, and the one compound predicate in the file (`_requires_ban`)
  is untouched 1.2/1.3 code.
  **One surviving mutant, judged equivalent rather than a gap**: widening
  `except PromptBuildError` to `except Exception` leaves all 482 green, because nothing
  `_compose_prompt` touches can raise anything else today — `__init__` only assigns, both
  build guards and `_select_template` raise `PromptBuildError`, the lookup is `.get` so it
  cannot `KeyError`, and both f-strings interpolate values `_reject_unrenderable_fields`
  already validated. Unreachable by structure, so no test has an input to assert on. It is
  a property of *today's* `build_prompt`, and it stops holding at **1.5/1.6** (which add
  fields to the composition) and at **2.1** (which moves the builder into the provider
  path): from then on a non-`PromptBuildError` escaping `_compose_prompt` propagates out of
  `execute` into the `BackgroundTask` context and strands the row `in_progress` until the
  sweep — exactly what the in-loop `except Exception` was written to prevent. Recorded here
  for those scenarios rather than opened as a 1.4 step.
- [~] adapters-discovery

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

**Two obligations placed on this scenario by 1.4's design (2026-08-05), copied here from
`decisions/prompt-builder-decision.md` because this file — not the ADR — is what a work
unit's author is obliged to read.** Note this is *Backend* 2.1; the story also has an
Integration 2.1 and a Security 2.1, and the ADR's first draft said "2.1" unqualified.

1. **Compose the prompt in the usecase, before the provider call** — not inside
   `GigaChatProvider.generate`. G5 asserts that a `PromptBuildError` means the provider was
   called **zero** times; a build anywhere inside the provider means it was called exactly
   once, so nesting the substitution there makes G5 unsatisfiable as written, and the
   cheapest escape from that red is to weaken G5. Composing upstream also makes the whole
   retry-of-an-unchangeable-value class structurally impossible rather than dependent on
   catch ordering.
2. **If the build nonetheless lands inside the adapter**, an adapter test must assert
   `GigaChatProvider.generate` propagates `PromptBuildError` **unwrapped** — not as
   `ProviderError`, not as `httpx.HTTPError`. Without it this scenario is free to widen
   that handler and the usecase-side guard stays green while never firing. Taking this
   path is a respecification of G5's count and must be recorded as one.

Also inherited: G14's guard test
(`test_gigachat_provider_prompt_agreement.py`) contains a ratchet that fails with an
instruction to **delete the file** once the provider delegates to `build_prompt` —
substitution is what makes G14 structurally unnecessary. Deleting it is this scenario's
job; silencing it is not.

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
