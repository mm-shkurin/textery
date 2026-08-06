# Decision: The prompt builder is a pure domain module over a narrow request

**Date**: 2026-08-01 (revised 2026-08-02 after the scenario 1.1 design-preview hazard
scan; revised again 2026-08-03 after the scenario 1.2 scan added G10–G13, widened G5 and
recorded six further out-of-diff findings; corrected 2026-08-04 after the review passes
over that revision — see "Corrections" below; revised again 2026-08-04 after the scenario
1.3 scan added G14–G17, gave G3 and G9 an owner, and corrected three claims the ban's
implementation had made stale — see "Revision (scenario 1.3)"; revised again 2026-08-05
after the scenario 1.4 scan overturned G17's prescribed mechanism and added G18 — see
"Revision (scenario 1.4)"; revised again 2026-08-06 after the scenario 1.5 scan replaced
strip-to-fixpoint with refusal and added G19–G28 — see "Revision (scenario 1.5)")
**Scenarios**: 1.1–1.6, 2.1

## Revision (scenario 1.5, 2026-08-06)

**Option D — refuse, do not strip.** All eight hazard groups re-dispatched from scratch;
group 8 dismissed as a block (re-derived, not inherited: no client surface, and the two
client-side rules that exist — `maxLength` 500 and a disabled-on-blank send button — are
already server-mirrored in `Generation.create` with a guard). Groups 1–7 fired, 26 GAPs,
collapsed to ten guards across the seams.

**The decision the scan forced, and it reverses this ADR's own standing instruction.**
The Edge Cases row "User text contains the delimiter token" has specified
**strip-to-fixpoint** since 2026-08-01, and G1 is written against it. Four groups
independently found that the loop is where this scenario's real hazards live, and none of
them is about correctness of the strip:

- **It is the only super-linear step on a per-request hot path** (group 6, and the 1.2
  scan's own ReDoS row): nested/overlapping fragments at the field cap make the cost
  n², and a field cap bounds n, not n².
- **Its iteration cap fails open** (group 5). The obvious mitigation for the cost is a
  maximum pass count, and the obvious behaviour at that cap is *proceed with
  partially-stripped text* — which is precisely the input the loop had not finished
  neutralizing. A security decision resolving permissively because of what a `while` loop
  yields, not because anyone chose it.
- **It is the one place an author reaches for module-level state** (group 3): a
  `_STRIP_CACHE[topic]` memo to buy the cost back, in a module whose entire
  multi-instance argument is "divergence requires a runtime write, and there is none".
- **It converts a per-request cost into a self-amplifying requeue** (group 3): the loop
  runs after `mark_in_progress()` on the event loop with no `to_thread`, so an adversarial
  topic can carry a row past `GENERATION_STALE_AFTER_MINUTES` and have the sweep start a
  second activation that spins identically — while blocking every other generation on
  that instance.
- **Its fixpoint is not assertable as specified** (group 2): NFC applied after the strip
  can re-compose a token out of combining characters that survived it, so
  `sanitize(sanitize(x)) == sanitize(x)` is a guard the strip needs and G9 does not give.

**Refusing dissolves all five rather than guarding them.** A single linear membership
test has no loop, no cap, no partial output, no memo incentive and no fixpoint. The four
gaps above are therefore recorded as **dissolved by the option chosen, not skipped** —
that distinction matters, because a later author who reinstates stripping reinstates every
one of them and will find no guard standing where the design removed the need for one.

**The cost of Option D, stated rather than discovered later.** Refusal is the strictly
less forgiving choice for rows already in the table: `Generation.__init__` applies none of
`create`'s validation, so a legacy row whose `topic` carries a newline or exceeds the cap
becomes permanently unbuildable in one deploy, where stripping would have salvaged it
(group 4). Accepted, on the size of the affected corpus rather than on principle — the
composer is a single-line input with `maxLength=500`, so no row the UI can produce is
affected; only API-crafted rows are, and a row that carries a forged instruction line is
one whose salvaged generation would have been the incident. The population reaching
`_fail_terminally` does widen, which matters because **Backend 3.2** owns the lifecycle
guard for that edge and lands after this scenario — noted there, not annexed here.

**The design.**

1. `topic` is NFC-normalized **on a local inside `build_prompt`, never on the entity**
   (G25). Group 3 found the entity is the natural place and the wrong one: the worker
   holds the `Generation` across a ~363 s window and every terminal path calls
   `storage.update(generation)`, so normalizing in place blind-writes the user's stored
   topic with sanitized text — an irreversible overwrite invisible to every prompt-level
   assertion.
2. **Re-cap after normalization** (G19), on `DocumentContent`'s precedent
   (`document_content.py:32-36`: raw cap → NFC → re-cap). NFC can grow the string, so a
   cap applied only before it is bypassable by choosing a composition form.
3. **Refuse** — `PromptBuildError` — if the normalized topic exceeds `MAX_TOPIC_LENGTH`
   (G19), contains any line-structuring character (G20), or forges the delimiter (G23).
4. The topic is interpolated wrapped in a **non-alphabetic** delimiter (G22).
5. Renderability is re-checked **after** normalization (G26).

**Two choices inside that, both forced by a specific hazard rather than by taste.**

- **The delimiter must be non-alphabetic.** `test_prompt_goldens.py:142` asserts every
  alphabetic character in the built prompt is Cyrillic — that is G13. Any Latin-lettered
  delimiter (`<<<TOPIC>>>`, `BEGIN_TOPIC`) is **red on arrival with no defect present**,
  and the cheapest fix is to widen G13's character class, which permanently re-opens the
  homoglyph hazard G13 exists to close. This is the same shape as the `_BAN_DEFERRED`
  escape the ADR blocked explicitly for G14; nothing blocked this one until now. Choosing
  a non-alphabetic token removes the collision instead of negotiating with it, and makes
  G13 and G22 mutually reinforcing rather than opposed. It also moots the case-folding
  question group 1 raised: a non-alphabetic token has no case, so no Turkish-`I` fold.
- **The forgery check runs on the NFKC fold; the output is NFC** (G23). NFC does not fold
  compatibility equivalents, so a fullwidth or `Cf`-interrupted variant of the token
  survives an NFC-only check as inert text and becomes the token the moment any consumer
  normalizes differently or the model simply reads it as visually identical. Checking the
  fold and emitting the NFC form closes that without letting NFKC mangle legitimate topics.

**The counterweight, because a strict sanitizer with no counterweight silently mutilates
valid input**: G24 pins a corpus of realistic Cyrillic topics — `«»` quotes, dashes,
parentheses, digits, `ё` — round-tripping into the prompt byte-identically. Without it the
delimiter choice is a coincidence rather than a decision, and `«»` in particular is common
in real Russian academic topics and would have been a plausible delimiter.

**The spec widening the 1.2 scan required, now actually made.** That scan recorded that
1.5's sentence must grow from "the delimiter token" to **any line-structuring character**,
and noted neither 1.2 nor 1.5 carried it. `_referat` is a `\n`-delimited instruction list,
so a `topic` containing `\n`, `\r\n`, U+2028, U+2029, U+0085, `\v` or `\f` forges an
instruction line the model reads as a peer of the template's own — **with a perfectly
correct delimiter**, because the delimiter wraps a field and does not escape per line.
G20 asserts on the built prompt's line count, not on the topic's contents, which is the
only form of the assertion that catches a forgery introduced downstream of the check.

**Routed elsewhere, not folded in**: the `FAILED`-not-absorbing lifecycle → Backend 3.2
(existing row; 1.5 widens the population reaching it). The sentinel-in-log guard →
Security 2.1 / 2.2 already own a widened version, **but** G27 is kept here as well and
deliberately so: group 7 found Security 2.1 as specified would go green while never
touching the error path, which is the exact "each pass assumed the other owned it" shape
this catalogue exists to break. Mutual exclusion on a second activation → Backend 3.2 /
3.4 (existing row).

### Corrections (2026-08-06, same day, after the review passes over `1a76bc74`)

Both passes independently reached the same false premise, and it was the premise the
whole availability trade rested on. Corrected before `red-usecase` could build against it.

**1. The composer is not a single-line input, so refusing line breaks refuses ordinary
users — and line-structuring characters are therefore collapsed, not refused.** The
paragraph above read "the composer is a single-line input with `maxLength=500`, so no row
the UI can produce is affected; only API-crafted rows are". False:
`frontend/src/features/generation/components/Composer.tsx:38-49` is a `<textarea rows={4}>`
whose `onKeyDown` intercepts only **Ctrl/Cmd**+Enter for send, so a plain Enter inserts a
newline, and `ChatWorkspace.tsx:45` trims the edges without touching interior breaks. A
user typing a two-line topic produces exactly the `\n` G20 was about to refuse — the
refused population is a routine UI path, not a legacy edge, and the failure they would get
is `GENERIC_FAILURE_MESSAGE`, i.e. "попробуйте позже" about a condition that is
deterministic forever.

The fix is not to widen the refusal's blast radius but to notice that the two hazards were
being treated as one. **A forged delimiter is hostile; a line break is punctuation.**
Line-structuring characters (`\n`, `\r\n`, U+2028, U+2029, U+0085, `\v`, `\f`) are
**replaced by a single space** before the delimiter check; a forged delimiter still
refuses. This costs none of what made stripping unacceptable: replacing a character with a
space is a **single linear pass that cannot regenerate its own input** — a space is not a
line break, so one pass reaches the fixpoint by construction. There is no loop, no
iteration cap, no partial-output fail-open and no memo incentive. The four dissolved
hazards stay dissolved; what is given up is only the claim that 1.5 refuses *everything*
it touches.

G20's assertion is unchanged in substance and stronger in form: it always asserted on the
**built prompt's line count**, not on the topic's contents, and that is exactly the
assertion that holds under replacement. Only its refusal clause moves.

**2. The refusal seam is still wrong for the cases that do refuse, and 1.5 does not fix
it — it names it.** A topic refused at build time was accepted at `POST /generations` with
a 201, because `generation_request_dto.py` applies no such rule and `Generation.create`
does not either. The user is told "try later" about something that can never succeed. The
honest scope statement: 1.5 owns the *prompt*, and moving validation into `create` changes
the API's accept/reject contract, which is **Backend 3.1**'s sentence ("A реферат request
is accepted"). Recorded as a new out-of-diff row with that owner rather than annexed here
— but G28 is amended to assert the persisted `error_message` for a `PromptBuildError` is
**distinguishable from the retry-exhaustion message**, because the premortem is right that
G28 as first written pinned "accept, then fail with retry-shaped advice" as correct.

**3. Normalization must not run before the cap.** Design step order was NFC-normalize →
re-cap → refuse, and G23 adds an NFKC fold. On the hydration path `topic` has **no** cap
at all, so that is two full `unicodedata.normalize` passes over an unbounded string, still
synchronous, still after `mark_in_progress()`. The event-loop hazard the revision above
declares dissolved was preserved with a smaller constant: O(n) on an unbounded n instead
of O(n²) on a bounded one. **A raw-length pre-check now runs first**, before any
normalization, and G19 gains the assertion that a grossly over-cap hydrated topic refuses
with `unicodedata.normalize` never called.

**4. G19's fixture requirements were mutually unsatisfiable** — the exact failure mode
G10 and G16 were first specified with. The row required a fixture both "wholly Cyrillic"
and "under the cap before NFC, over it after". No character in U+0400–U+052F grows under
NFC, so no wholly-Cyrillic string can cross the cap by normalizing. Split: the MAX/MAX+1
boundary fixture is wholly Cyrillic (that is where the code-point-vs-byte unit distinction
matters); the growth fixture uses a character that actually grows and need not be Cyrillic.

**5. G28's rationale named a failure that cannot occur.** It said `except Exception`
retries a non-`PromptBuildError` escaping the build and bills the provider twice. That
`except` is *inside* the retry loop and wraps only `provider.generate`; `_compose_prompt`
is outside it. The real consequence is the opposite and worse: the exception escapes
`execute()` into the `BackgroundTask` with the row already persisted `in_progress`, where
nothing answers for it until the sweep. G28's assertion is rewritten to that.

**Three smaller ones.** `test_referat_ban.py:227` is 84 lines past EOF (the file is 143
lines; the `_BAN_DEFERRED` ratchet is at ~103) — a dangling citation under an analogy G22
restates three times. G20's line count must use `str.splitlines()`, since
`split("\n")` is blind to U+2028/2029/0085/`\v`/`\f`, which is the exact set the widening
exists for. And G24's corpus must be NFC to begin with, or a legitimately-decomposed entry
is red on arrival with no defect present.

**The "dissolved" list is five, and it is enumerated once.** The first draft said "five"
in one sentence, "four" in the next, and named two different four-member sets across the
two artifacts — in a record whose entire purpose is that a future author reinstating
stripping recovers the *full* list. Canonically: (1) the wall-clock/iteration bound, (2)
fail-closed behaviour at an iteration cap, (3) `sanitize(sanitize(x)) == sanitize(x)`,
(4) the module-level-memo assertion, (5) the sweep-requeue amplification. All five, and
the replacement in correction 1 reinstates none of them.

## Revision (scenario 1.4, 2026-08-05)

All eight hazard groups re-dispatched from scratch against the 1.4 design (group 8
dismissed as a block — a domain prompt-template design has no client surface, derived
rather than assumed). Groups 1–7 fired, 21 GAPs. Two things changed that are not
bookkeeping.

**1. G17's prescribed mechanism was wrong, and this revision reverses it.** The full
argument is in G17's restated row. Short form: the boot-time raise it mandated trades a
missing dict entry for a fleet-wide outage, and the pre-deploy catch it was reaching for
is obtainable from a test instead. Option D — runtime `PromptBuildError` plus a
completeness *test* — was chosen over the boot raise (Option A), over "runtime refusal and
nothing else" (Option C), and over test-only-with-the-retry-mapping-deferred (Option B).
This matters beyond 1.4 because G17 was written by the 1.3 scan and read as settled; a
scenario author implementing it verbatim would have shipped the outage.

**2. G5 is the seam guard every group flagged, it already exists here, and it is still
unimplemented — but 2.1 can make it unsatisfiable as written.** Groups 1, 2, 3, 4, 5, 6
and 7 each independently flagged "a `PromptBuildError` retried on a value that cannot
change on attempt 2", each assuming another pass owned it. It is not a new guard: it is
**G5**, written at the 1.1 scan. `grep -rn PromptBuildError` outside `backend/domain/`
still returns nothing, so G5 has never been implemented, and
`generate_document.py`'s `except Exception` retries the error with a 1.0–1.5s backoff.

The new part is a **placement obligation on 2.1**. G5 asserts "provider called **zero**
times", which presumes the prompt is built at the call site — the usecase — before the
provider is reached. If 2.1 substitutes `build_prompt` *inside* `GigaChatProvider.generate`
(the obvious reading of "the provider sends the prompt it was given"), the provider is
necessarily called before the build can fail, and G5 becomes unsatisfiable as written —
the likeliest outcome being that whoever meets the red quietly weakens G5 rather than
noticing the placement caused it. So 2.1 carries two named obligations, recorded here
rather than left to that scenario's discretion:

- Compose the prompt **in the usecase, before the provider call**. This is the
  compute-then-commit mitigation, and it makes the whole retry-of-an-unchangeable-value
  class structurally impossible instead of dependent on catch ordering. It also keeps G5
  literally true. **Corrected 2026-08-05**: this bullet first offered "or at minimum before
  `gigachat_provider.py`'s `try`" as a fallback, which contradicts the next sentence — G5
  asserts the provider is called **zero** times, and any build inside
  `GigaChatProvider.generate` means the provider was called exactly once, `try` or no `try`.
  The fallback sanctioned precisely the path this paragraph exists to prevent: an author
  takes it, meets a red G5, and weakens G5. It is withdrawn. Building inside the adapter is
  a respecification of G5's count, not a minimum-effort variant of it, and it requires
  saying so explicitly rather than reaching for it under a sanctioned-sounding "at minimum".
- If the build nonetheless ends up inside the adapter, an adapter test must assert
  `GigaChatProvider.generate` propagates `PromptBuildError` **unwrapped** — not as
  `ProviderError`, not as `httpx.HTTPError`. Without it, 2.1 is free to widen that
  handler and the usecase-side guard stays green while never firing.

**Which 2.1.** Both obligations above are on **Backend 2.1** ("The provider sends the
prompt it was given") — the scenario that performs the substitution. This story has three
scenarios numbered 2.1 (Backend, Integration "A provider error still ends the generation as
failed", and Security "The prompt is not written to the log verbatim"), and the first draft
of this revision said "2.1" unqualified throughout. G5's own implementation is 1.4's, per
its owner row. The obligations are also copied inline under Backend 2.1's block in
`progress-backend.md`, because that file — not this one — is what a scenario author is
obliged to read before starting a work unit.



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
| `volume_pages` is a `bool` (added 2026-08-04, after 1.3's GREEN shipped the guard and the coverage pass found nothing exercised it) | `PromptBuildError`. It is the one unrenderable volume the range check cannot catch: `True == 1 == MIN_VOLUME_PAGES`, so it passes the comparison and renders `(True стр.)` — a Latin-lettered artifact in a prompt every other guard here keeps Cyrillic. Listed separately from the row above precisely because it is *in* range; folded into that row's enumeration it reads as another out-of-range value and the type check looks deletable. |
| `topic` is `None`, empty, or whitespace-only (same hydration path; `_required_topic` runs only in `create`) | `PromptBuildError` rather than emitting `на тему: None` |
| Composed prompt exceeds the ceiling | Per-field caps are 500 / 2000 / 2000, so the composed prompt has a bound the design states explicitly and enforces on the built string — the hydration path applies no per-field cap at all. Over the ceiling raises `PromptBuildError`. |
| `document_type` in a non-NFC normal form | Normalized before the subscript, so the реферат template is still selected. |
| `document_type` outside `SUPPORTED_DOCUMENT_TYPES` | `UnsupportedDocumentTypeError`; the worker lands the row `failed` with the sanctioned generic message, without retrying. |
| User text contains the delimiter token | **Reversed 2026-08-06 (1.5): refused, not stripped.** This row read "NFC-normalized first, then the token is stripped **to fixpoint**" from 2026-08-01 until the 1.5 scan, and G1 was written against that wording. Four hazard groups found the loop, not the strip's correctness, was where this scenario's hazards lived — super-linear cost on a per-request path, an iteration cap that fails open on partially-stripped text, a module-level memo incentive, and a self-amplifying sweep requeue. `PromptBuildError` instead: one linear membership test, no loop and none of the four. The check runs on the **NFKC fold** (NFC does not fold compatibility equivalents, so a fullwidth token would survive an NFC-only check); the emitted form is NFC. See "Revision (scenario 1.5)" for why the legacy-row cost of refusing was accepted. |
| `topic` contains a line-structuring character (`\n`, `\r\n`, U+2028, U+2029, U+0085, `\v`, `\f`) | `PromptBuildError`. `_referat` is a `\n`-delimited instruction list, so these forge an instruction line the model reads as a peer of the template's own — **even with a correct delimiter**, since the delimiter wraps a field rather than escaping per line. This is the spec widening the 1.2 scan required and no scenario had made. |
| `topic` above `MAX_TOPIC_LENGTH` on the hydration path, or above it only *after* NFC | `PromptBuildError` from the **post**-normalization check. NFC can grow the string, so a pre-NFC-only cap is bypassable by choosing a composition form — `DocumentContent` (`document_content.py:32-36`) is the precedent, and its re-cap is the part a naive reading drops. The cap is counted in **code points**, matching `Generation.create`; the overhead constants G10/G15 pin are counted in **UTF-8 bytes**. Two units, ~1.8× apart on Cyrillic, and the fixture must be wholly Cyrillic so they differ. |
| `topic` is non-blank before normalization and blank after | `PromptBuildError`, not a blank topic slot. `_is_renderable_topic` runs before normalization and uses a bare `.strip()`, which — unlike `Generation._required_topic` — does not remove `Cf` format characters, so a `Cf`-only topic passes it and would render `на тему:  (5 стр.)` on a billed call. |
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
| G1 | **Restated 2026-08-06 (1.5) — the mechanism it asserted was withdrawn.** It read: "Delimiter in `topic` in a non-NFC / combining form → zero tokens in the built prompt. Splice fixture (one removal pass reconstructs the token) → zero tokens." The splice half was a *fixpoint* assertion, and 1.5 replaced stripping with refusal, so there is no removal pass for a splice to defeat — the fixture is unwritable against the chosen design. As it stands now: a `topic` carrying the delimiter in NFC form, in a combining/decomposed form, or in a compatibility form → `PromptBuildError`. The non-NFC half survives intact and is the load-bearing one; G23 carries the compatibility-form half, which an NFC-only check misses. **Note for anyone reinstating stripping**: the splice assertion becomes necessary again the moment a removal pass exists, and nothing else in this table would cover it. |
| G2 | `build_prompt` at maximum field lengths, and one past them via `__init__`, → the stated ceiling holds or `PromptBuildError`. **Disjunctive by design — it is satisfied either way, so it cannot go red when a type flips from "holds" to "raises". G10 is the non-disjunctive half.** |
| G3 | `volume_pages` at `0`, negative, and above `MAX_VOLUME_PAGES` → `PromptBuildError`, same as the `None` case. |
| G4 | `topic` `None` / empty / whitespace-only → `PromptBuildError`. |
| G5 | Any `PromptBuildError` at the call site → provider called **zero** times, `sleep` awaited **zero** times, row `failed` after exactly one `storage.update` past `mark_in_progress`. Goes red if the build drifts inside the retry loop. **Its fixture must reach the error via a *ceiling* breach as well as via an unsupported type — the two arrive from different call paths, and a fixture that only ever raises the unknown-type error leaves the ceiling path's retry behaviour unasserted.** **Owner assigned 2026-08-05 (1.4): `red-usecase` / `green-usecase` of scenario 1.4.** G5 has existed since the 1.1 scan, has been re-flagged by seven hazard groups across three scans, and has never been implemented — `grep -rn PromptBuildError` outside `backend/domain/` still returns nothing — precisely because every pass assumed another owned it and the row carried no owner. It is assigned here rather than to a later scenario because **1.4 is the commit that removes the loud guard**: Option D deletes the module-scope `assert` and converts a missing template into a `PromptBuildError`, which `generate_document.py`'s `except Exception` today retries with a backoff and then reports to the user as "попробуйте позже" — advice that is false forever — at a log severity shared with routine provider blips. Removing the loud failure while the quiet one stays unmapped is paying for the reversal on credit. 1.4 carries both halves or neither. |
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
| G17 | **Restated 2026-08-05 (1.4) — the earlier wording prescribed the wrong mechanism.** It read: "fails at boot as a raised, named exception, not a bare `assert`". The diagnosis was right (`python -O` strips `assert`, so the fifth-type guard holds by accident of interpreter invocation) but the prescribed cure was worse than the disease: a module-scope raise means a deploy where `SUPPORTED_DOCUMENT_TYPES` gains a fifth type before `_TEMPLATES` does takes down **every instance at import** — including generations of the four types that work — so the blast radius of one missing dict entry is the whole service. `ImportError` specifically is also the wrong class: it is the one exception routinely swallowed by optional-import `try/except ImportError` in loaders and DI wiring, which converts a fail-closed crash into a silent skip. As it stands now, two halves: (a) `build_prompt` raises `PromptBuildError(f"no prompt template for {document_type}")` on the missing key, so the failure is named, terminal and scoped to the one affected request; (b) the bare `assert` is **deleted** and replaced by a domain test that removes a template and asserts the refusal — so a missing template is red in CI *before* deploy, which is the pre-deploy catch the boot-raise was reaching for, with no production crash path at all. Note (b) is what makes this different from "just delete the check": the completeness claim survives, it moves from an `-O`-strippable runtime statement into a test, which `-O` cannot strip. **Corrected 2026-08-05, same day, after both review passes over `dd9b0f72` reached it independently**: half (b) as first written did **not** move the completeness claim, it dropped it. A test that removes a key and asserts `PromptBuildError` exercises the *refusal mechanism*; it is green whether `_TEMPLATES` covers `SUPPORTED_DOCUMENT_TYPES` or not, so the named hazard — a fifth type added to the tuple before the dict — passes it unchanged. The deleted `assert` was a **set equality** and caught both directions: a supported type with no template, and a stale template for a type dropped from the tuple. Half (b) therefore requires **two** tests, not one: the removal test above, **and** an explicit `set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES)` assertion, both directions, in `backend/domain/tests/generation/`. Relying on the parametrized suites to catch it incidentally is not acceptable here and this ADR elsewhere refuses exactly that — G14 is the precedent, having been scoped away from `SUPPORTED_DOCUMENT_TYPES` for a legitimate reason, which is how incidental coverage evaporates. The reverse direction (an extra key) is caught by nothing today. **Owner: 1.4.** |
| G18 | The per-type assertion over `SUPPORTED_DOCUMENT_TYPES` is **type-discriminating, not truthiness**. "A non-empty prompt is produced for every one of them" is satisfied by a mojibake prompt, a replacement-character prompt, and a prompt whose Cyrillic type name was decoded under the wrong charset — so `assert built` admits a fifth type on a check that cannot fail for any reason a reader would care about. Assert per type that the built prompt carries that type's own text and lands on the correct side of the ban branch (`BAN_SENTENCE` present for every type in `TYPES_REQUIRING_SOURCE_BAN - _BAN_DEFERRED`, absent for доклад while the freeze holds). The ban table has no completeness assertion of its own anywhere — G12 asserts the ban over the derived set, but nothing asserts *per type* which side it landed on, so a fifth type silently inherits "ban applies" with no case exercising it. **Rationale narrowed 2026-08-05**: the mojibake half of the argument above is already guarded — `test_prompt_goldens.py`'s `test_should_spell_every_type_s_prompt_entirely_in_cyrillic` is implemented and parametrized over all types, so a wrong-charset prompt is red today (that is G13). G18's genuinely new content is the **per-type ban-side discrimination**, and an author who reads the mojibake framing as the point will write the half that already exists and skip the half that does not. **Owner: 1.4.** |
| G13 | **Scope restated 2026-08-04 (1.3)**: asserted per type over every built prompt in `SUPPORTED_DOCUMENT_TYPES`, matching G6's scope rather than the ban sentence alone. 1.3 goldens `на тему:` and `стр.` for the first time, and `с`, `о`, `р`, `а`, `е` — **four** of which appear in those two fragments (`а` and `е` in `на тему:`, `с` and `р` in `стр.`) — are exactly the homoglyph-bearing characters the rationale below names. Every alphabetic character in the built prompt is Cyrillic (`unicodedata.name(ch)` starts with `CYRILLIC`). **Rationale corrected 2026-08-04**: the earlier claim that список/литературы/источники are spelled "entirely" from homoglyph-bearing characters is false — `п`, `и`, `к`, `л`, `ы`, `ч`, `н` have no Latin lookalike. The real hazard is narrower and still real: `с`, `о`, `р`, `а`, `е` **do** have identical Latin glyphs, and one of them mistyped inside `список` or `источники` renders the same, ships a corrupted instruction, and passes a hand-typed expected literal that carries the same mistake. Because only *some* characters are substitutable, a presence check on a subword is **not** an adequate substitute — which is precisely what the wrong rationale would have licensed. Only the character-class assertion over the whole string catches it. |

G19–G28 were folded in from the **scenario 1.5** scan (2026-08-06; all eight groups
re-dispatched from scratch — group 8 re-derived and dismissed as a block, groups 1–7
fired). All ten are **Backend 1.5's** unless a row says otherwise.

| ID | Guard |
|----|-------|
| G19 | Three fixtures, and the third was added by the corrections below. **(a)** `topic` at `MAX_TOPIC_LENGTH` builds; at `MAX_TOPIC_LENGTH + 1`, hydrated via `Generation.__init__`, → `PromptBuildError`. **Non-disjunctive** — one branch asserted, not G2's "holds *or* raises", which is why G2 cannot cover this. This fixture is **wholly Cyrillic**, so the code-point cap and the UTF-8 byte overhead G10/G15 pin are visibly different quantities rather than one self-equal number. **(b)** The composition-form half: a topic **under** the cap before NFC and **over** it after → refused by the post-NFC check, so the cap is not bypassable by choosing a normal form. **This fixture must not be wholly Cyrillic** — no character in U+0400–U+052F grows under NFC, so requiring both properties of one string (as the first draft did) makes the half unwritable, which is precisely how G10 and G16 were first specified. **(c)** A grossly over-cap hydrated topic refuses with `unicodedata.normalize` **never called** — the raw-length pre-check runs ahead of any normalization. Without (c) the design's own step order does two full normalization passes over an unbounded string on the event loop after `mark_in_progress()`, which is the sweep-requeue hazard this revision claims to have dissolved, preserved with a smaller constant. This guard is the ADR's own twice-recorded unowned row (`_reject_unrenderable_fields` has no `topic` cap at all), reached independently by groups 1, 5, 6, 7 and 8. |
| G20 | The built prompt's line count — counted with `str.splitlines()`, **not** `split("\n")`, which is blind to U+2028/2029/0085/`\v`/`\f` and so blind to the exact set this widening exists for — equals the template's own, for every hostile fixture and every type in `SUPPORTED_DOCUMENT_TYPES`. A `topic` containing `\n`, `\r\n`, U+2028, U+2029, U+0085, `\v` or `\f` has each replaced by a single space (**corrected 2026-08-06 from "→ `PromptBuildError`"** — the composer is a `<textarea>`, so a line break is ordinary punctuation from a routine UI path, not a hostile artefact; see Corrections). **Asserted on the built prompt, not on the topic**, which is the only form that catches a line break introduced downstream of the check — and the form that is unchanged by the switch from refusal to replacement. **Parametrized over every user-controlled string field `PromptRequest` carries, derived from `PromptRequest.__init__`'s signature rather than hand-listed**, so the fourth and fifth fields 1.6 adds (`requirements`, `extra_wishes` — both `str \| None`, both reaching the composed prompt per the ceiling row) are red until covered. Hand-listing here would open a silent hole in a later scenario, which is the shape G27 exists to break; the codebase's own precedent for deriving rather than listing is `TYPES_REQUIRING_SOURCE_BAN`. |
| G21 | The built prompt contains exactly one opening and one closing delimiter, at the expected offsets, for every type in `SUPPORTED_DOCUMENT_TYPES`. G1 asserts the token is absent from the *user text*; this asserts the *structure of the output*, which is what a forgery actually attacks — a template that forgets a closing token, or a refusal that lets one of a spliced pair through, leaves an unbalanced structure G1 is green on. |
| G22 | The delimiter contains **no alphabetic character**, asserted on the constant itself. G13 asserts every alphabetic character in the built prompt is Cyrillic, so a Latin-lettered delimiter is red on arrival with no defect present — and the cheapest fix is widening G13's character class, which permanently re-opens the homoglyph hazard G13 exists to close. G22 blocks that escape the way `test_referat_ban.py`'s `_BAN_DEFERRED` ratchet (~line 103, in `TestTheBanScopeIsDerived`) blocks the widen-the-freeze one. **Citation corrected 2026-08-06**: this row first cited `test_referat_ban.py:227`, which is 84 lines past that file's EOF — a dangling anchor under an analogy G22 restates three times. Corollary worth stating because it removes a guard rather than adding one: a non-alphabetic token has no case, so the case-folding hazard group 1 raised (an exact-match strip missing a case variant; a case-insensitive one meeting the Turkish `I`) cannot arise. |
| G23 | A **compatibility-form** delimiter (fullwidth variants, U+2039/U+203A) and a `Cf`-interrupted delimiter → `PromptBuildError`. The refusal decides on the **NFKC fold** of the topic while the emitted topic is **NFC**: NFC does not fold compatibility equivalents, so an NFC-only check passes a fullwidth forgery through as inert text that becomes the token the moment any consumer normalizes differently — or that the model simply reads as visually identical. |
| G24 | A corpus of realistic Cyrillic topics — `«»` quotes, em/en dashes, parentheses, digits, `ё`, ordinary punctuation — round-trips into the built prompt **byte-identically**. **The corpus entries must themselves be NFC** (added 2026-08-06): a legitimately-decomposed entry (`и` + U+0306) is transformed by a correct implementation, so it would be red on arrival with no defect present, and the cheapest escape is to weaken the assertion from byte-identity to something vaguer. The corpus doubles as the counterweight to G23's NFKC fold, which folds real Russian typography (ligatures, fullwidth digits) and would otherwise refuse benign topics with nothing going red. The counterweight without which the delimiter choice is a coincidence rather than a decision: a delimiter drawn from characters that occur in real Russian academic topics mutilates valid input silently and turns nothing else in this table red. `«»` is the specific trap — idiomatic in Russian topic titles and an otherwise attractive delimiter. |
| G25 | After `_compose_prompt(generation)`, `generation.topic` is byte-identical to the hydrated value, and no `storage.update` call carries a topic differing from the one read — for a topic that *is* transformed on the way into the prompt. Normalization happens on a local inside `build_prompt` and never on the entity. The worker holds the `Generation` across a ~363 s window and every terminal path persists it, so in-place normalization blind-writes the user's stored topic with sanitized text: an irreversible overwrite of persisted user data, invisible to every prompt-level assertion. G9 is green either way — it constrains the builder's inputs and module state, not the caller's entity, and `PromptRequest` is constructed fresh at the call site. |
| G26 | A `topic` non-blank before normalization and blank after → `PromptBuildError`, not a blank topic slot. Reachable because `_is_renderable_topic` runs *before* normalization and uses a bare `.strip()`, which — unlike `Generation._required_topic` — does not remove `Cf` format characters. Without it a `Cf`-only topic renders `на тему:  (5 стр.)` and is billed. This is the `DocumentContent` re-cap pattern applied to renderability rather than to length: check, transform, **re-check**. |
| G27 | Two halves, and the second is the one that has never existed anywhere in this repo. **(a)** A ratchet over the module's *whole* `PromptBuildError` message family asserting each is a fixed string with **no interpolation slot** — not the current per-message opt-in, under which any message 1.5 adds is guarded only by what 1.5 itself writes. The in-file precedent points the wrong way: `_select_template` raises `f"no prompt template for {document_type}"`, so an author copying the nearest sibling copies the interpolating one. **(b)** Seed a sentinel inside `topic`, drive **every** `PromptBuildError` family through `GenerateDocument.execute`, and assert the sentinel is absent from `str(exc)`, from `caplog` at error level, and from the persisted `error_message` (which must equal the sanctioned constant). `grep -rln caplog` over `backend/domain/tests/` and `backend/usecase/tests/` returns one unrelated file, so no captured-log assertion exists at any level today. **Kept here even though Security 2.1/2.2 own a widened version** — deliberately, because Security 2.1 as specified asserts absence at info level on the happy path and would go green while never touching the error path, which is exactly the shape where each pass assumes the other owned it. |
| G28 | G5's parametrization extended to **every** refusal reason 1.5 introduces — over-cap topic (raw and post-NFC), forged delimiter, blank-after-normalization — each asserting provider called zero times, `sleep` awaited zero times, exactly two `storage.update` calls. (Line-structuring characters are no longer a refusal reason; see Corrections.) G5's own row already demands its fixture reach the error by more than one call path "because the two arrive from different call paths"; by that argument the paths added here are unasserted. **Rationale corrected 2026-08-06 — the first version named a failure that cannot occur.** It said `generate_document.py`'s `except Exception` retries a non-`PromptBuildError` escaping the build and bills the provider twice. That `except` is *inside* the retry loop and wraps only `await self._provider.generate(generation)`; `_compose_prompt` is at line 77, outside it. So a `ValueError` out of `unicodedata` is retried **zero** times and bills nothing — and the real consequence is worse in the other direction: it escapes `execute()` into the `BackgroundTask` with the row already persisted `in_progress` at line 74, where nothing answers for it until the stale sweep. Left as written, this row would have sent `red-usecase` after a double-bill that cannot happen while leaving the stranded-row path unasserted, and the prescribed "exactly two `storage.update` calls" would have gone red for that case for the wrong reason (the true count is one). **Second half, added the same day**: assert the persisted `error_message` for a `PromptBuildError` is **distinguishable from the retry-exhaustion message**. As first written G28 pinned "accept the request, then fail it with retry-shaped advice" as correct behaviour — `_fail_terminally` writes `GENERIC_FAILURE_MESSAGE` ("попробуйте позже") for a condition that is deterministic forever, at a severity shared with routine provider blips. |

**Dissolved by Option D, not skipped.** Four gaps the scan raised have no guard because
the design removed the mechanism, and they are recorded rather than dropped so that
reinstating stripping reinstates them: the strip loop's wall-clock/iteration bound (no
loop), its fail-closed behaviour at an iteration cap (no cap), `sanitize(sanitize(x)) ==
sanitize(x)` (no sanitize stage), and the module-level-memo assertion (no cost to memoize
away). A later author who brings back a removal pass will find no guard standing where
this design removed the need for one.

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

Added by the scenario 1.4 scan (2026-08-05). Findings already recorded by the 1.1–1.3
scans (outbound idempotency, the sweep-vs-deadline margin, 4xx-retried-like-5xx, the
error-path log leak) are **not** repeated here — they fired again, and their existing rows
above still hold.

| Finding | Owner |
|---------|-------|
| **`topic` is length-capped in code points but never NFC-normalized.** The same visual Cyrillic topic passes or fails `MAX_TOPIC_LENGTH` depending on composition form, and reaches the template in whichever form it arrived — on text where G10/G15 already make the UTF-8 byte length load-bearing. **Exemplar corrected 2026-08-05**: this row first said "unlike `Email` and `Password`, which both normalize *before* their length check". That is backwards, and copying it would have produced the wrong fix. `email.py:28-30` and `password.py:20` cap **first** and normalize **second**, deliberately — the docstring says an adversarial input must not reach the more expensive checks. The class that actually solves this problem is **`DocumentContent`** (`document_content.py:32-36`): raw cap → NFC → **re-cap**, with a docstring noting NFC can *grow* the string and that the post-NFC cap is the authoritative one. That re-cap is the part a naive reading drops. | **Backend 1.5** — "The topic cannot displace the template's instructions". Reassigned 2026-08-05: first recorded as unowned, but the 1.2-scan row three rows above already widens 1.5's spec to cover topic line-structuring characters, and the ReDoS row assigns topic stripping to 1.5/1.6. Normalization form is the same surface; leaving it unowned meant losing it when 1.5 widened anyway |
| **`_reject_unrenderable_fields` has no maximum `topic` length at all.** `Generation.create` caps at 500, but the hydration path bypasses `create` — the same bypass the function's own docstring documents for the range check. Once 2.1 substitutes the builder into the provider, an unbounded `topic` is interpolated and shipped downstream. A boundary-only cap cannot close this. | No scenario owns this. 3.3 owns boundary rejection of the *document type*, not `topic` length |
| **`Generation`'s status lifecycle is driven by raw setters with no transition graph**, and `__init__` accepts `status` as a free-form `str`. `FAILED` is not absorbing, skip and reverse edges (`PENDING → COMPLETED`, `FAILED → PENDING`) are reachable, and an entity can be constructed directly into a terminal state or into a status outside the four. Adding a new terminal edge (G5's `fail()`) writes into this lifecycle without pinning it. | Backend 3.2 (end-to-end completion) — the scenario that exercises the lifecycle |
| **Poison message: nothing asserts one permanently-unbuildable generation does not block the ones queued behind it.** G5 covers the single failing item terminating; it says nothing about the queue making progress past it. | Load scenarios / Backend 3.2 |
| **Retry storm: G5 is a single-caller guard.** A systemic cause — a migration leaving `volume_pages` null across many rows — makes many in-flight generations fail deterministically and re-issue against GigaChat in lockstep, against the downstream rate limit `ExpectedLoad.md` names as the binding constraint. Nothing drives M concurrent callers through one failure and asserts attempts are capped and spread. | Load scenarios |
| **A 200 with an empty body flows into `generation.complete(content)`**, landing the row `completed` with an empty document the client cannot distinguish from a real result. The provider's failure modes are enumerated only for `httpx.HTTPError`. | Integration 2.1 (a provider error ends the generation as failed) |
Added by the scenario 1.5 scan and its review passes (2026-08-06):

| Finding | Owner |
|---------|-------|
| **The accept/refuse seam is split across two layers with no guard that they agree.** A topic 1.5 refuses at build time was accepted at `POST /api/v1/generations` with a 201 — `generation_request_dto.py` declares `topic: str \| None` with no pattern, and `Generation.create` checks length and blankness only. The user therefore gets an accepted request that fails deterministically with "попробуйте позже". Moving the rule into `create` is the fix, and it changes the API's accept/reject contract — a `ValidationException`/422 where there is a 201 today — which is a contract decision this scenario does not own. The guard, when it lands: a test parametrized over every 1.5 refusal reason asserting `Generation.create` rejects the same input `build_prompt` rejects, so the two validation sets cannot drift. | **Backend 3.1** ("A реферат request is accepted") — the scenario whose sentence is the request contract. G28's amended second half is 1.5's partial mitigation, not a substitute |
| **N-1 deploy ordering for the fifth type.** Adding a type needs both the code tuple and the `ck_generations_document_type` CHECK to change; during a rolling deploy of a multi-instance backend both orderings occur (new code writing a fifth-type row the old CHECK rejects; old code reading a row whose type it does not define). G7 asserts the two agree at build time, not across a deploy, and no unknown-enum policy exists for the *read* side — `Generation.__init__` hydrating an unknown type has no stated behaviour. | No scenario owns this. G7 covers the build-time half only |
