# Decision: The prompt builder is a pure domain module over a narrow request

**Date**: 2026-08-01 (revised 2026-08-02 after the scenario 1.1 design-preview hazard
scan; revised again 2026-08-03 after the scenario 1.2 scan added G10–G13, widened G5 and
recorded six further out-of-diff findings)
**Scenarios**: 1.1–1.6, 2.1

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
  template rather than merely unused by today's templates.
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
| эссе / сочинение | Rendered through the same pre-change f-string today, so each gets its own golden `==` too. The refactor is asserted lossless for every type, not asserted for one and assumed for the rest. |

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
| G10 | `build_prompt` for **реферат specifically**, with `topic`/`requirements`/`extra_wishes` each at their exact cap (500 / 2000 / 2000), **returns** — it does not raise — and the built string is at or under a ceiling pinned as a named constant in an **explicit unit**. The unit is `len(prompt.encode("utf-8"))`: the template is Cyrillic, so a code-point ceiling and a byte ceiling differ by ~2× on exactly this text, and an unstated unit makes the bound unfalsifiable. Goes red when template text grows past the remaining headroom — which is the point, because "each obligation gets its own sentence" invites more sentences and реферат already carries the largest fixed overhead of the four types. |
| G11 | The ban is emitted **after every user-interpolated field** in the built prompt. Asserted on position, not presence: a prompt that contains the ban sentence while a hostile `topic` preceding it countermands the ban satisfies the scenario's own substring assertion and has still failed. Neither G1 (delimiter token) nor G2 (length) would go red on it, and scenario 1.2 is the scenario that chooses the ban's position, so the ordering guard has no other owner. |
| G12 | The ban is asserted over a **declared set** of types that require it, not over the literal `REFERAT`. The existing exhaustiveness machinery (`set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)`, G6, G7) pins that every type *has* a template and that its text is stable — none of it pins that a type needing the ban *carries* it. A fifth long-form type routed to `_plain` would ship with no ban, at boot, with every test green: fail-open in the permissive direction. |
| G13 | Every letter in the built реферат prompt is Cyrillic (`unicodedata.name(ch)` starts with `CYRILLIC` for each alphabetic character). `список`, `литературы` and `источники` are spelled entirely from characters with Latin homoglyphs — `с`, `е`, `о`, `р`, `а` — so a single Latin `c` typed into the template renders identically, ships a corrupted instruction to the model, and passes a hand-typed expected literal carrying the same homoglyph. A presence assertion cannot catch this; only a character-class assertion can. |

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
