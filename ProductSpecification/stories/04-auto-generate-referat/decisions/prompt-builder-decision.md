# Decision: The prompt builder is a pure domain module over a narrow request

**Date**: 2026-08-01 (revised 2026-08-02 after the scenario 1.1 design-preview hazard
scan; revised again 2026-08-03 after the scenario 1.2 scan added G10–G13, widened G5 and
recorded six further out-of-diff findings; corrected 2026-08-04 after the review passes
over that revision — see "Corrections" below; revised again 2026-08-04 after the scenario
1.3 scan added G14–G17, gave G3 and G9 an owner, and corrected three claims the ban's
implementation had made stale — see "Revision (scenario 1.3)")
**Scenarios**: 1.1–1.6, 2.1

## Revision (scenario 1.3, 2026-08-04)

Scenario 1.3 is the golden `==` on the built prompt, and drafting it surfaced that three
statements in this file describe a design that no longer matches the code. All eight
hazard groups were re-dispatched from scratch against the 1.3 design (group 3 dismissed as
a block — a pure deterministic builder has no shared state, no persistence and no read
path); seventeen GAPs collapsed to seven distinct guards across the seams.

| Claim as written before this revision | What is actually true |
|---|---|
| Edge Cases: "эссе / сочинение — rendered through the same pre-change f-string today, so each gets its own golden `==` too" | False since the 2026-08-04 ban widening in the Corrections section directly above. эссе and сочинение now carry the ban, so their goldens are the pre-change text **plus** `"\n" + BAN_SENTENCE`. Only доклад is byte-identical, and only because `_BAN_DEFERRED` freezes it. A 1.3 author who trusted this row would have pinned the wrong string, found it red, and "fixed" it by widening `_BAN_DEFERRED` — silently reverting the ban for two of the four types. |
| ~~"Rejected table / 'Chosen': the ban lives inside `_referat`"~~ — **this row was itself false; corrected below the table** | The Rejected table's three rows are the `Generation` method, the class-per-type registry and the random nonce; none mentions where the ban is emitted, and the "Chosen" paragraph names only the module, `_TEMPLATES` and the delimiter. The only text placing the ban inside `_referat` is the Corrections narrative, which is already labelled as corrected history. The substantive fact is still worth stating: the ban ships in `build_prompt` gated by `_requires_ban` (commit `f5ae0842`), because per-template emission re-creates the hand-maintained list one level down — whoever adds a fifth type writes a fresh template function and must remember the ban line inside it. But no section of this ADR needed editing for that, and the row as first written sent the next reader to fix two sections that were not wrong. |
| `_plain`'s docstring: "kept as-is so that the goldens for доклад/эссе/сочинение land against the pre-refactor text" | Same stale claim, second copy, in the source file rather than here. Two of its three types now differ from the pre-refactor text by one line. |

Two guards that had no owning scenario now have one, because 1.3 is the scenario that
makes them writable:

- **G3** (`volume_pages` at `None` / `0` / negative / above `MAX_VOLUME_PAGES` →
  `PromptBuildError`) belongs to **1.3**. It was unowned, and five of the eight hazard
  groups independently flagged the same thing: 1.3 is the change that makes the field
  *render*, so it is the change that makes `доклад на тему: X (None стр.)` reachable. The
  value is `int | None` the whole way down — `generation_request_dto.py` defaults it to
  `None`, and `Generation.__init__` (the hydration path) applies no range check, only
  `create` does. This finally puts `PromptBuildError` in the code; the ADR has specified
  it since 2026-08-01 and `grep` has never found it.
  **Scope limit**: 1.3 raises it, and does **not** map it at the call site. That mapping
  is G5's, and `build_prompt` has no caller until 2.1.
- **G9** (determinism and no mutation) belongs to **1.3**. Also unowned. A golden asserts
  the first call only, so a builder that memoized into a mutated buffer, or that
  normalized `document_type` in place, passes every golden while the retry's second
  attempt sends a different string than the first.
- **G4** (`topic` `None` / empty / whitespace-only → `PromptBuildError`) belongs to
  **1.3** as well. Added 2026-08-04 after the review passes: the owner sweep above assigned
  G3 and missed G4, though the argument for G4 is *stronger*. `_plain` has interpolated
  `topic` since 1.1, so `на тему: None` is reachable **today**, whereas G3's hazard only
  becomes reachable with the clause this scenario adds. `_required_topic` runs in `create`
  and not in `__init__`, the same asymmetry that makes G3 necessary. Since 1.3 is the
  scenario that introduces `PromptBuildError`, it is the cheapest possible moment to raise
  it for both fields rather than build the exception for one and leave the other open.

**`PromptBuildError`'s base class is pinned here, not left to the implementation.** It
derives from the project's domain-exception base and **not** from `ValidationException`,
and the intent it carries into G5 is: *a prompt build failure is deterministic and must not
be retried*. Recorded because deferring the call-site *mapping* to G5/2.1 does not defer
the *default*: `generate_document.py:61` catches bare `Exception` and retries
`MAX_PROVIDER_ATTEMPTS` times with backoff, so an unmapped `PromptBuildError` is treated as
transient — a value that cannot change on attempt 2, burning the retry budget and landing
the user on the generic failure message with nothing in the log naming `volume_pages`.
Deriving from `ValidationException` is the other wrong answer: it drags in
`error_code`/`message` and the REST handler's 422 mapping, which is meaningless on a
`BackgroundTask` path and pre-empts G5's choice. 1.3 chooses the base; G5 at 2.1 inherits
it as a contract rather than as an accident.

## Corrections (2026-08-04)

The `agent-review` and `premortem` passes over commit `9c004c94` found that the 1.2
revision asserted four things that are not true, and that its central scoping decision was
an accident rather than a judgement. Recorded here rather than silently rewritten,
because the rest of this file is what the next reader trusts.

| Claim as written 2026-08-03 | What is actually true |
|---|---|
| Option B "would redden scenario 1.3's доклад golden" | Scenario 1.3 is entirely unstarted. The only доклад golden today is `backend/adapters/generation_provider/tests/provider/test_gigachat_provider_generate.py:51` — a golden on `GigaChatProvider`'s **own** f-string, and the provider does not call `build_prompt` yet (scenario 2.1 owns that substitution). A global append to `build_prompt` would redden nothing today. Option A is still chosen, on the corrected reasoning below. |
| G10 asserts at `topic`/`requirements`/`extra_wishes` caps | `PromptRequest.__init__` takes `document_type` and `topic` only. The other fields arrive with the scenarios that read them. G10 as written was unrunnable, and its realistic downgrade to topic-only would have made it vacuous. Restated below. |
| список/литературы/источники are spelled "entirely from characters with Latin homoglyphs" | False. `п`, `и`, `к`, `л`, `ы`, `ч`, `н` have no Latin homoglyph, and no word in the three satisfies "entirely". The G13 guard is still right; the rationale under it was wrong and would have misled whoever wrote the test into accepting a presence check on a subword. |
| The unknown-type path is unreachable (Schema note) / is reachable and retried (out-of-diff row) | Both are in this file and they contradict. Reconciled: the CHECK constraint makes an out-of-set `document_type` unreachable from **steady-state data**, and the hydration path plus a deploy step make it reachable **in transit**. So the `KeyError`-is-retried finding stands, and the Schema note's "not reachable" is true only of the narrower claim it makes. Neither sentence is deleted; the scope of each is now stated. |

The scoping decision the premortem caught: Option A confined the ban to `_referat` for
reasons that were entirely about test mechanics, and never argued that эссе and сочинение
do not need it. They route to `_plain`, they are accepted by the API today (Security 3.1
pins that open deliberately), and a fabricated bibliography harms a student in an эссе
exactly as much as in a реферат. **Decided 2026-08-04: all four types require the ban.**
See `TYPES_REQUIRING_SOURCE_BAN` under Model.

Moving prompt composition out of `GigaChatProvider` needs a home, and the hazard scan
turned two of the obvious choices into liabilities: passing the `Generation` entity lets a
template ship `owner_id` to a third party, and a random-nonce delimiter would fix prompt
injection by destroying the purity that the retry path depends on.

| Rejected | Why |
|----------|-----|
| Method on `Generation` (`generation.build_prompt()`) | Hands every template the whole entity — `owner_id`, `content`, `error_message` — so a future template can interpolate server-owned data into text sent to GigaChat. `generation.py` is also already ~165 lines against a 200-line cap, so the table would have to be split out regardless. |
| One class per type behind a registry | Registration happens at runtime, so `set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)` cannot fail at import — the one guard that makes a fifth type a build failure instead of a worker failure. Four classes for four pure functions. |
| Per-request random nonce as the data delimiter | Strongest injection defence, but the prompt stops being a pure function of the request. The retry path sends one prompt across both attempts, so a nonce makes attempt 2 a different request than attempt 1, and the "prompt is deterministic" guard becomes unwritable. |

**Chosen**: a pure module `backend/domain/src/generation/prompt_template.py` exposing
`build_prompt(request: PromptRequest) -> str`, dispatching through a module-level
`_TEMPLATES` dict keyed by document type. The delimiter is fixed, and the token is
normalized and then stripped to fixpoint from user text before interpolation —
deterministic, so purity survives.

## Model

- `PromptRequest` — new value object carrying only `document_type`, `topic`,
  `volume_pages`, `requirements`, `extra_wishes`. Deliberately not the `Generation`
  entity: `owner_id`, `content` and `error_message` are structurally unreachable from a
  template rather than merely unused by today's templates. The fields arrive with the
  scenarios that read them — `document_type`/`topic` at 1.1, `volume_pages` at **1.3**
  (it is what makes `_plain` byte-identical to the provider's f-string), and
  `requirements`/`extra_wishes` at 1.6. G16 is the ratchet that keeps the list from
  growing past this one.
- `build_prompt(request)` — pure, stateless, no clock, no I/O. NFC-normalizes
  `document_type` before the lookup, because `Generation.__init__` (the storage
  hydration path) does not normalize.
- `PromptBuildError` — new domain exception, the base for every reason a prompt cannot
  be built. `UnsupportedDocumentTypeError` is one subclass. The base exists because the
  call site must map *every* build failure to the terminal branch, not only the
  unknown-type one (see the call site below).
- `_TEMPLATES` — module-level dict of pure builder callables, never written at runtime.
  This is not the in-memory state `.claude/rules/coding-rules.md` bans: divergence across
  instances requires a runtime write, and there is none. An import-time assertion pins
  `set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)`.
- `TYPES_REQUIRING_SOURCE_BAN` — **equals `SUPPORTED_DOCUMENT_TYPES`.** Every type gets
  the ban, because the harm (a student submits a document carrying invented sources) does
  not depend on which of the four was asked for. Written as an equality rather than a
  hand-listed tuple on purpose: a hand-maintained list defeats its own guard, since the
  developer who forgets to wire the ban into a fifth type's template is the same one who
  forgets to add it to the list.
- `_BAN_DEFERRED` — `(DOKLAD,)`, and this is a **scheduling** exclusion, not a judgement
  about доклад. Story 1 is being finished in `textery-editor` / `textery-projects`
  against today's доклад output, so changing that text now reddens their tests for a
  reason unrelated to their work. The unblock condition is story 1 landing; the follow-up
  belongs to scenario 2.1, which is already rewriting the provider hand-off.
  The two guards over this are deliberately in tension, and the tension is the alarm:
  G12 asserts every type in `TYPES_REQUIRING_SOURCE_BAN - _BAN_DEFERRED` carries the ban,
  while G6's доклад golden pins the frozen text. Emptying `_BAN_DEFERRED` before story 1
  lands turns G6 red — which is exactly the coordination check that ought to fire, rather
  than a comment nobody reads.
- The ban sentence itself, pinned here because G11 asserts its position and G13 its
  character class, and neither is writable against an unquoted string:
  `Не включай список литературы и не ссылайся на источники.`
  Emitted as its own sentence on its own line, last, consistent with `_referat`'s
  one-marker-per-section contract — a ban folded into an existing sentence would break
  the `_sentence_with` helper the 1.1 tests already rely on.
- `GenerationProvider.generate` — port changes from taking a `Generation` to taking the
  built prompt. `GigaChatProvider` composes no text.
- Call site: `GenerateDocument.execute`, **once, after `mark_in_progress()` and before the
  retry loop** — not once per attempt. Before `mark_in_progress()` the row would stay
  `pending` and the stale sweep would cycle it forever; inside the retry loop a
  deterministic error burns both attempts plus backoff, and `generate_document.py`'s
  deliberate catch-all `except Exception` would absorb a domain error as a provider
  error. `PromptBuildError` — the base, so every build failure is covered — maps straight
  to a terminal `fail()` with the sanctioned generic message and no retry.

## Schema note (corrected)

An earlier draft of this ADR asserted the `generations` table carries no CHECK constraint
on `document_type`. It does: migration `d0e1f2a3b4c5` adds `ck_generations_document_type`,
deriving its allowlist from `SUPPORTED_DOCUMENT_TYPES`. `Generation._validate_document_type`'s
docstring repeats the same stale claim and should be corrected when that file is next
touched. The consequence for this design: a row whose `document_type` is outside the
supported set is not reachable from steady-state data — only across a deploy step or from
a direct write. `build_prompt`'s raise stays as defence in depth, but it is no longer the
only guard, and the NFC-normalization rationale rests on the hydration path alone.

The constraint bakes the four values into SQL at migration time. Growing
`SUPPORTED_DOCUMENT_TYPES` therefore satisfies the import-time `_TEMPLATES` assertion and
every unit test while the constraint rejects the INSERT at runtime — the failure lands on
a user rather than at boot, which is the opposite of what this ADR claims elsewhere. G7
below is the guard that closes it.

## Edge Cases

| Case | Behavior |
|------|----------|
| `requirements` / `extra_wishes` is `None` or `""` | The section is omitted entirely — no dangling header, no orphaned delimiter pair. The literal string `None` never reaches the model. |
| `volume_pages` is `None`, `0`, negative, or above `MAX_VOLUME_PAGES` (all reachable via `__init__` on the hydration path, which applies no range check — only `create` does) | `PromptBuildError` rather than emitting `0 стр.` / `-3 стр.` |
| `topic` is `None`, empty, or whitespace-only (same hydration path; `_required_topic` runs only in `create`) | `PromptBuildError` rather than emitting `на тему: None` |
| Composed prompt exceeds the ceiling | Per-field caps are 500 / 2000 / 2000, so the composed prompt has a bound the design states explicitly and enforces on the built string — the hydration path applies no per-field cap at all. Over the ceiling raises `PromptBuildError`. |
| `document_type` in a non-NFC normal form | Normalized before the subscript, so the реферат template is still selected. |
| `document_type` outside `SUPPORTED_DOCUMENT_TYPES` | `UnsupportedDocumentTypeError`; the worker lands the row `failed` with the sanctioned generic message, without retrying. |
| User text contains the delimiter token | User text is NFC-normalized first, then the token is stripped **to fixpoint** — one pass can splice a fresh occurrence out of the surrounding text. Asserted at maximum field lengths, not only on short fixtures. |
| A fifth document type is added without a template | Import-time assertion fails at boot, plus a test on the same equality. Never a worker failure. |
| доклад | Byte-identical to the string `GigaChatProvider` composed before this story, pinned by a golden `==` test — story 1 is being finished elsewhere against that exact output. |
| эссе / сочинение | **Corrected 2026-08-04 (1.3).** Each gets its own golden `==` — the refactor is asserted lossless for every type, not asserted for one and assumed for the rest — but the expected text is the pre-change f-string **plus** `"\n" + BAN_SENTENCE`, not the pre-change f-string alone. They route to `_plain` and they are in `TYPES_REQUIRING_SOURCE_BAN`; only доклад is byte-identical, and only for as long as `_BAN_DEFERRED` holds it. Writing these goldens against the bare pre-change text makes them red on arrival, and the cheapest-looking fix — adding эссе and сочинение to `_BAN_DEFERRED` — silently reverts the ban for half the types that need it. |

## Forced Guards

Every row is a test that must go red on the hazard. G1–G9 were folded in from the
scenario 1.1 design-preview hazard scan (groups 1–7 fired; group 8 dismissed as out of
altitude). G10–G13 were folded in from the **scenario 1.2** scan (2026-08-03; all eight
groups re-dispatched from scratch — group 2 clear, group 8 re-derived and dismissed as a
block, groups 1/3/4/5/6/7 fired).

| ID | Guard |
|----|-------|
| G1 | Delimiter in `topic` in a non-NFC / combining form → zero tokens in the built prompt. Splice fixture (one removal pass reconstructs the token) → zero tokens. |
| G2 | `build_prompt` at maximum field lengths, and one past them via `__init__`, → the stated ceiling holds or `PromptBuildError`. **Disjunctive by design — it is satisfied either way, so it cannot go red when a type flips from "holds" to "raises". G10 is the non-disjunctive half.** |
| G3 | `volume_pages` at `0`, negative, and above `MAX_VOLUME_PAGES` → `PromptBuildError`, same as the `None` case. |
| G4 | `topic` `None` / empty / whitespace-only → `PromptBuildError`. |
| G5 | Any `PromptBuildError` at the call site → provider called **zero** times, `sleep` awaited **zero** times, row `failed` after exactly one `storage.update` past `mark_in_progress`. Goes red if the build drifts inside the retry loop. **Its fixture must reach the error via a *ceiling* breach as well as via an unsupported type — the two arrive from different call paths, and a fixture that only ever raises the unknown-type error leaves the ceiling path's retry behaviour unasserted.** |
| G6 | Golden `==` on the built prompt for every type in `SUPPORTED_DOCUMENT_TYPES`, not only доклад. |
| G7 | The live `ck_generations_document_type` allowlist equals `SUPPORTED_DOCUMENT_TYPES` — growing the tuple without a follow-up migration is red at build time. |
| G8 | The unsupported-type failure emits a signal naming `generation.id` and the offending `document_type`, distinct from the retry-exhaustion signal; the persisted `error_message` and any client-visible payload equal the sanctioned constant and carry no fragment of the raw type, no exception class name, no traceback marker. |
| G9 | `build_prompt` on the same request twice returns an identical string, and module state (`_TEMPLATES` keys and callable identities) is unchanged across a batch of calls across all four types. This is the guard the nonce rejection rests on. |
| G10 | **Restated 2026-08-04** — the 2026-08-03 wording asserted at `requirements`/`extra_wishes` caps, which `PromptRequest` does not carry, so it was unrunnable and would have been quietly downgraded to something vacuous. As it stands now: assert the реферат template's **fixed overhead** — the built prompt's length with `topic` empty — against a named constant, in `len(...encode("utf-8"))` bytes. The unit is explicit because the template is Cyrillic and a code-point bound and a byte bound differ by ~2× on exactly this text. This is writable against today's two-field `PromptRequest`, and it is the half that actually guards the hazard: adding a sixth sentence moves the fixed overhead and turns the assertion red, whether or not the user's fields are at their caps. The at-caps composed-prompt assertion is the **other** half and belongs to whichever scenario adds `requirements`/`extra_wishes` to `PromptRequest` (1.6) — recorded there rather than presupposed here. |
| G11 | The ban is emitted **after every user-interpolated field** in the built prompt. Asserted on position, not presence: a prompt that contains the ban sentence while a hostile `topic` preceding it countermands the ban satisfies the scenario's own substring assertion and has still failed. Neither G1 (delimiter token) nor G2 (length) would go red on it, and scenario 1.2 is the scenario that chooses the ban's position, so the ordering guard has no other owner. |
| G12 | **Restated 2026-08-04** — the earlier wording said "a declared set" without declaring one, which relocated the fail-open instead of closing it: a hand-maintained list is forgotten by the same developer who forgets the ban. As it stands now: assert the ban over `TYPES_REQUIRING_SOURCE_BAN - _BAN_DEFERRED`, where the first **is** `SUPPORTED_DOCUMENT_TYPES` (an equality, so a fifth type joins it with no human step) and the second is the story-1 freeze. A fifth long-form type therefore arrives already inside the asserted set and goes red until its template carries the ban. Paired with G6's доклад golden, which goes red if `_BAN_DEFERRED` is emptied before story 1 lands. |
| G14 | The provider and the domain agree on the prompt, asserted between the two **live composers** rather than between two hand-typed literals: drive `GigaChatProvider.generate` and assert the posted `content` equals `build_prompt(...)` built from the same `Generation`. Until 2.1 substitutes one for the other there are two independently-editable definitions of the same text — `_plain` and the f-string at `gigachat_provider.py:113-116` — each pinned by its own golden, so **either can be edited alone with nothing red** and this scenario's whole claim ("unchanged by the move") dies silently. Four hazard groups reached this from different directions. Golden-vs-golden cannot force it; only an assertion whose two sides are the two composers can. **Scoped 2026-08-04 to доклад alone, and the scope is load-bearing**: the provider appends no ban, `build_prompt` appends one for every type outside `_BAN_DEFERRED`, so parameterizing G14 over `SUPPORTED_DOCUMENT_TYPES` the way G6 and G13 are parameterized makes it red on arrival for эссе/сочинение/реферат with no defect present — and the cheapest escape from that red is to widen `_BAN_DEFERRED`, i.e. to unban them. (That escape is already blocked: `test_referat_prompt.py:227` asserts `tuple(_BAN_DEFERRED) == (DOKLAD,)`. The scope note exists so a 1.3 author does not reach for it honestly and then have to back it out.) The other three types stay unpinned across the two composers until 2.1 removes one of them. **Home: an adapter test under `backend/adapters/generation_provider/tests/`, not `red-usecase`** — it drives `GigaChatProvider`, and a domain or usecase test importing an adapter inverts the dependency rule. It resolves at runtime only because `backend/pyproject.toml` puts every layer root on one `pythonpath`, so the violation would land silently. |
| G15 | `_plain`'s overhead in UTF-8 bytes against a named constant. G10 covers the one template 1.3 does **not** change; this scenario adds the ` ({volume_pages} стр.)` clause to the other three, and nothing currently bounds their length. **Terms stated 2026-08-04, because G10's do not transfer**: `_referat` hardcodes its type name, so it has one genuinely fixed overhead. `_plain` interpolates `document_type`, whose byte length differs per type (`доклад` 12, `эссе` 8, `сочинение` 18), and `volume_pages`, whose digit count is 1 or 2. Assert `len(built) - len(document_type) - len(str(volume_pages))` in UTF-8 bytes against **one** constant covering all three `_plain` types, in the same subtract-the-variable-part style the реферат overhead test already uses for its probe topic. A per-type constant table is the acceptable alternative; pinning one type at one volume is not — it is vacuous for the other two and blind to a digit-width change, and that cheap exit is exactly what made G10's first formulation unwritable. |
| G16 | `PromptRequest.__init__`'s accepted parameter set is exactly `(document_type, topic, volume_pages)` — inspected, not implied — and a `Generation`'s `owner_id`, `content`, `error_message`, `id`, `status` and `version` cannot reach it. The narrowness of this object is the entire reason the "method on `Generation`" option was rejected, and adding `owner_id` to it today turns no test red. **It is a ratchet on *what* may be added, not on *whether***: 1.6 legitimately grows the set to five with `requirements`/`extra_wishes`, and updating G16's expected tuple is that scenario's job. What G16 forbids is a field arriving from `Generation` without a scenario deciding it should — the guard goes red either way, and the difference is whether an author has a design telling them the growth was planned. |
| G17 | The `_TEMPLATES` completeness check fails at boot as a **raised, named exception**, not a bare `assert`. `python -O` / `PYTHONOPTIMIZE` strips `assert` statements, so the guard that makes a fifth type a build failure instead of a worker failure currently holds by accident of how the interpreter is invoked. **Owner: 1.4** — "every supported document type yields a prompt" is that scenario's sentence. |
| G13 | **Scope restated 2026-08-04 (1.3)**: asserted per type over every built prompt in `SUPPORTED_DOCUMENT_TYPES`, matching G6's scope rather than the ban sentence alone. 1.3 goldens `на тему:` and `стр.` for the first time, and `с`, `о`, `р`, `а`, `е` — **four** of which appear in those two fragments (`а` and `е` in `на тему:`, `с` and `р` in `стр.`) — are exactly the homoglyph-bearing characters the rationale below names. Every alphabetic character in the built prompt is Cyrillic (`unicodedata.name(ch)` starts with `CYRILLIC`). **Rationale corrected 2026-08-04**: the earlier claim that список/литературы/источники are spelled "entirely" from homoglyph-bearing characters is false — `п`, `и`, `к`, `л`, `ы`, `ч`, `н` have no Latin lookalike. The real hazard is narrower and still real: `с`, `о`, `р`, `а`, `е` **do** have identical Latin glyphs, and one of them mistyped inside `список` or `источники` renders the same, ships a corrupted instruction, and passes a hand-typed expected literal that carries the same mistake. Because only *some* characters are substitutable, a presence check on a subword is **not** an adequate substitute — which is precisely what the wrong rationale would have licensed. Only the character-class assertion over the whole string catches it. |

## Out-of-Diff Findings

These fired during the scan at pipeline altitude. They are real, and they are not this
design's diff — recorded here, mapped to the scenario that already owns them, so no pass
assumes another owned it.

| Finding | Owner |
|---------|-------|
| The billed completion carries no idempotency key. A read timeout the client abandoned but the server completed is charged twice; `PromptRequest` structurally excludes `generation.id`, the only stable identity a key could derive from. | Backend 3.4 (duplicate submission does not generate twice) |
| Lost update: the worker holds a stale `Generation` across a ~363 s window while the sweep can requeue the row; the late `complete()` blind-writes over it. `version` exists on the entity; no test asserts the CAS. | Backend 3.2 (end-to-end completion) |
| Deadline budget: `MAX_PROVIDER_ATTEMPTS × READ_TIMEOUT_SECONDS + backoff ≈ 363 s` against `GENERATION_STALE_AFTER_MINUTES` 600 s — a factor of 1.65, asserted nowhere. Raising the timeout or adding an attempt makes the sweep requeue a live row. | Integration 2.2 (provider timeout ends the generation as failed) |
| `GigaChatProvider` collapses every `httpx.HTTPError` into one `ProviderError`, so a deterministic 4xx is retried like a transient 5xx. The port signature is being rewritten anyway — cheap moment to split it. | Integration 2.1 (provider error ends the generation as failed) |
| Migration `d0e1f2a3b4c5` bulk-rewrites `document_type` on rows outside the allowlist with no status filter, including `completed` rows whose `content` describes the original type. `downgrade()` drops the constraint only; the original value is unrecoverable. No test references the migration. | No scenario owns this — needs a task if it is to be fixed |
| `generate_document.py:69-75` interpolates the caught `error` into the log, and `ProviderError` is built from `str(httpx.HTTPError)`, which carries the upstream URL and status detail. | Security 2.2 (a provider failure does not leak its raw body) |

Added by the scenario 1.2 scan (2026-08-03):

| Finding | Owner |
|---------|-------|
| **This ADR describes two mechanisms that do not exist in the code.** `grep` for `UnsupportedDocumentType` and for `unicodedata` under `backend/domain/src/generation/` returns nothing: `build_prompt` is a bare `_TEMPLATES[...]` subscript with no `PromptBuildError`, no subclass, and no NFC normalization. So an unknown or non-NFC `document_type` raises `KeyError` today — which is not a `PromptBuildError`, so the call site's terminal-`fail()` mapping misses it, `generate_document.py`'s catch-all absorbs it as a *provider* error, and it is **retried**. The specified behaviour and the actual behaviour are opposites. | Backend 1.4 (every supported type yields a prompt) / 3.3 (unsupported type is rejected) |
| Second activation of one generation. `GENERATION_STALE_AFTER_MINUTES` can requeue a row while a live worker is still inside its retry loop (the same 1.65× margin recorded above), and because the ADR pins the build to happen once per activation, each activation builds its own prompt and issues its own billed completion. The missing assertion is mutual exclusion — a DB-backed lease on `generation.id` such that a second activation acquires no work — not the two consequences already listed. | Backend 3.2 / 3.4 |
| `PromptBuildError` messages are unconstrained. The natural ceiling message quotes the offending field, and `generate_document.py` interpolates the caught error into the log, so the user's own `topic` reaches the log through the error path. Security 2.1 asserts absence at info level on the **happy** path only, so an error-level leak passes it untouched. Needs a sentinel seeded in each user field, driven through **every** `PromptBuildError` family, asserted absent from `str(exc)`, from captured logs at every level, and from the persisted `error_message`. | Security 2.1 / 2.2 — both need their scope widened to the error path |
| Strip-to-fixpoint is a repeat-until-stable loop over user text. G1 asserts it is *correct* at maximum field lengths; nothing asserts it is *bounded in time*. On nested/overlapping delimiter fragments at the 2000-char cap the cost is super-linear in input length — ReDoS-shaped, on a per-request hot path. A field cap bounds n; it does not bound n². | Backend 1.5 / 1.6 (the scenarios that implement the stripping) |
| Raw newline injection in `topic`. `_referat` is a `\n`-delimited instruction list, so a `topic` containing `\n` / `\r\n` / ` ` forges an additional instruction line. G1 covers the delimiter **token** only. The scan's finding is that **neither** 1.2 nor 1.5 currently carries this — 1.5's spec has to be widened from "the delimiter token" to "any line-structuring character". | Backend 1.5 — spec widening required, not merely implementation |
| Nothing validates the returned content against the ban. The scenario asserts the prompt *instructs*; a model that ignores it produces a реферат with an invented bibliography, which is persisted and rendered unchallenged. No automated guard is possible while the provider is a fixture-returning stub. | `progress.md` § Open — judge one real generation by hand before the story is called done |
