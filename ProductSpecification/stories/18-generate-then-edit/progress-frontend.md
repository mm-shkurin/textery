# Story 18: Generate → edit — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Selecting a type goes straight to generation
- [x] red-selenium — analytical RED (skipped; live run deferred to green-selenium). New `test_generate_flow_acceptance.py` (35) + `generate_flow_statements.py` (37) + conftest fixture. Asserts pick-doklad-type → `[data-testid='generation-generating']` visible AND `MODE_MODAL` NOT shown. Predicted RED: TimeoutException on `generation-generating` — current `useFlowNavigation.selectType` sets `step='mode'` (mode modal), no generating surface renders. New contract testid `generation-generating` (also 1.2's subject). test-review PASS 0 fixes. **Owed for green-selenium (non-gating, agent-review+premortem converge): (1) transient-surface flake — `assert_generation_started` waits on `generation-generating` with `live_session=True`; a fast real backend can transition past the generating state between polls → spurious TimeoutException indistinguishable from regression. green-selenium must pin generation to a deterministic pending window (slow/stubbed poll) before un-skip. (2) `assert_no_mode_modal_shown` (invisibility_of MODE_MODAL) passes vacuously for ANY modal-absent state (landing/error/editor) — only earns its keep because `assert_generation_started` runs first; coupled to (1). Consider adding a positive assertion that exactly one POST /generations fired (base DSL has `_count_requests_to`). Nit: redundant `element.is_displayed()` after `_wait_for_visible`.**
- [x] red-frontend — live vitest RED on `useFlowNavigation` hook seam. Added `it.skip` test: `selectType('doklad')` → `step==='form'` + `mode==='auto'` (straight to generation, no `'mode'` step). RED confirmed: `AssertionError: expected 'mode' to be 'form'` (useFlowNavigation.test.tsx:78) — current `selectType` sets `step='mode'`, `mode=null`. Matched prediction. test-review +1 fix: added `documentType==='doklad'` + `openDocumentId===null` (openDocumentId null is what makes ChatWorkspace POST a NEW generation vs GET existing). Suite 12 pass / 1 skip. **green note:** flipping `selectType` to `setStep('form')+setMode('auto')` breaks the existing "walks type then mode" test + makes `selectMode`/`backToModeModal`/`'mode'` step dead for the create path — handle in green/refactor. **Owed for green (agent-review+premortem, converge): (A, IMPORTANT) contract testid `[data-testid='generation-generating']` (used by red-selenium 1.1) does NOT exist — `ChatWorkspace.tsx` exposes `chat-panel`/`doc-area`, and `GenerationUiState` is `idle|pending|completed|failed` (no `generating`). green MUST reconcile: either add a `generation-generating` testid on the pending/generating surface, or repoint the Selenium locator to an existing testid + generation `pending` state. Also: at `step='form'&mode='auto'` the workspace renders `idle` unless `selectType` also triggers generation — pin that `form+auto` actually kicks off generation (renderer-level or Selenium), not just hook state. (B) `backFromEditor` for a new (non-history) doc falls through to `backToModeModal()`→`step='mode'` (now forward-unreachable but Back still routes there → orphaned modal); green must repoint Back + remove/retire dead `selectMode`/`backToModeModal`/`'mode'` wiring. Sibling tests `walks type then mode`, `returns a newly created document to the mode modal`, `unwinds the whole flow on sign-out` will break — green must preserve the sign-out poll-stop guarantee (add a single-step `selectType`-only logout-unwind test). (C) `mode` collapses to constant `'auto'` on create path — decide if generating-vs-editor should key off `openDocumentId` alone.**
- [x] green-frontend — `selectType` now sets `step='form'`+`mode='auto'` (straight to generation). Removed `selectMode`/`backToModeModal`/`'mode'` step; DELETED `ModeModal.tsx`/`.css`/test (dead). FlowLanding step narrowed to `landing|type`. `backFromEditor` (new/non-history doc) → `generation.reset()`+`step='type'` (history path unchanged → `history`). Added `data-testid='generation-generating'` on DocArea **pending** branch (contract A resolved by adding testid, not repointing locator). Siblings updated w/o weakening: removed `walks type then mode`; `...to mode modal`→`...to type step`; sign-out unwind converted to single-step `selectType`-only, poll-stop preserved. App.test.tsx integration updated (dropped 2 mode-modal→manual-editor entry tests; ManualEditor covered by own suite + history path). Suite **526 pass / 0 fail**, tsc clean. **CAVEAT (blocks green-selenium 1.1):** did NOT auto-submit generation at `form+auto` — `createGeneration` needs a real topic, none exists until composer used; workspace opens on idle composer, so `generation-generating` (pending) is not yet reachable on load. Auto-start + deterministic pending window owed to red-frontend-api/align-design BEFORE green-selenium 1.1 un-skips (remove-marker-only must not run prematurely). **Review passes on 916ab0a (refactor NO-OP; agent-review CONCERNS/4 + premortem CONCERNS/2):** (1) FIXED IN THIS UNIT — commit broke Story 5 `test_mode_modal_acceptance.py` (waited on removed `MODE_MODAL`); marked `@pytest.mark.skip` OBSOLETE (mode modal removed by Story 18). `ModeModalStatements` fixture + `MODE_CARD_AUTO` base locator now unused (harmless; retire in a later cleanup). (2) OWED — **manual-create path now unreachable**: `mode='manual' && openDocumentId===null` is dead (only `openDocumentFromHistory` sets manual, always with an id), so Story 5's blank/non-AI editor create is gone. INTENDED by Story 18 (unify), to be restored by **scenario 6.1** "blank document from scratch" — but nothing marks it intentionally-down; if story ships before 6.1 it's a silent regression. 6.1 MUST add an integration guard that a signed-in user reaches a blank ManualEditor. (3) OWED — vacuous hook test: `useFlowNavigation` 1.1 test named "goes straight to generation" only asserts hook state; the generating surface/POST is not proven at renderer level (composer idle on load). Covered by the green-selenium block caveat + owed auto-start. (4) MINOR — dead `backToTypeModal` hook export (only its own test references it) + unreachable `backFromEditor` new-doc else-branch (→`type`); trim when 6.1 wires create-path editor. (5) REMOTE — ChatWorkspace has no back-to-type affordance; mis-picked type only escapable via sign-out (pre-existing, low-sev).
- [x] red-frontend-api — live vitest RED on the `generationApi` wire contract. New `generationApi.documentType.test.ts` (`it.skip`): `createGeneration(topic, 'referat')` must send `document_type: 'реферат'`; today `createGeneration` takes only a topic and hardcodes `WIRE_DOCUMENT_TYPE[DEFAULT_DOCUMENT_TYPE]`, so whichever type card is pressed the wire says `доклад`. RED confirmed: `AssertionError: expected 'доклад' to be 'реферат'` — matched prediction verbatim (type/message/expected/received/location/1-failed all matched). **Subject choice:** red-agent deliberately did NOT write the "picking a type fires exactly one auto-POST" test the green-frontend caveat asked for — the pending-state half is already pinned by `useGeneration.test.ts:18`, and the auto-POST half is hook/renderer wiring, not `generationApi`. More importantly its premise is contested: `createGeneration` needs a real topic, none exists until the composer is used, an empty-topic POST is a backend 422 — so a RED demanding auto-POST would force a wrong implementation. **The topic-source question (where does a topic come from before the first POST?) is a product decision owed to `align-design`; green-selenium 1.1 stays blocked.** test-review +6 fixes applied: full-body `toEqual` (caught unasserted `volume_pages`), exact URL `/api/v1/generations` + method `POST` + exact header set, `Idempotency-Key` pinned via `vi.stubGlobal('crypto', {randomUUID})`, return-value `toEqual({generationId,status})` (mapping regression was invisible), `toHaveBeenCalledTimes(1)` (duplicate POST passed before). File 65L. Suite `src/features/generation/api/__tests__`: 23 pass / 0 fail / 1 skip. **Owed to green-frontend-api:** widen to `createGeneration(topic, documentType)` mapping via `WIRE_DOCUMENT_TYPE`; thread the type through `useGeneration.submit` (`useGeneration.ts:130`, topic-only today) from `ChatWorkspace`/`DocumentGenerationFlow` via `flow.documentType` (already in hook state). **Review passes on 6b4af28 (refactor NO-OP; agent-review CONCERNS/4; premortem BLOCK/2):** (1) FIXED IN THIS UNIT — the commit turned the branch tip un-buildable: `it.skip` suppresses execution but not compilation, `tsconfig.app.json` includes `src`, so `npm run typecheck` and `npm run build` (`tsc -b && vite build`, both in `.github/workflows/frontend-ci.yml`) failed with `TS2554: Expected 1 arguments, but got 2`. Note a bare `npx tsc --noEmit` reports clean — `tsconfig.json` is `"files": []` + project references, so only the `-b` form checks anything; **the red-phase gate must run `npm run typecheck`, not bare tsc**. Fixed with a `@ts-expect-error` on the call line: keeps CI green while skipped and is self-removing (an unused `@ts-expect-error` is itself an error once green widens the signature). Verified: typecheck clean, suite 23 pass / 1 skip. (2) OWED, corrects the line above — `generationApi.test.ts` never passes a type: lines 29/51/71/83/96 all call `createGeneration(topic)` with ONE argument. Those five sibling call sites plus the sole production caller `useGeneration.ts:130` keep compiling only if green makes the second parameter **optional with a `DEFAULT_DOCUMENT_TYPE` default**. That is a design decision green must make deliberately, not a satisfied precondition — a required parameter breaks all six at once. (3) OWED, IMPORTANT — the optional-default shape means **green can satisfy this RED, satisfy typecheck, keep all 526 tests green, and still never thread `flow.documentType` through**, leaving the wire hardcoded to `доклад`. This unit pins the contract one layer below where the defect lives. A caller-level test is required: drive `useGeneration.submit` / `ChatWorkspace` after `selectType('referat')` and assert the `createGeneration` spy received `'referat'`. (4) OWED, planning gap — the auto-start guard the green-frontend caveat owes to "red-frontend-api/align-design" now has no step left to land in: remaining steps are `green-frontend-api`, `align-design`, `green-selenium`, `demo`, and none is a red step (`green-selenium` only un-skips, `align-design` is a product decision, `demo` is observation). Either insert a new red step after `align-design`, or green-selenium 1.1's recorded block resolves by accident when someone un-skips. (5) MINOR — this unit's commit message says "whichever type card the user presses the wire always says доклад", but `doklad` is the only entry with `available: true` in `shared/documentTypes.ts`, so the defect is latent, not user-reachable today. The test file's own header comment states this correctly; the commit message (the project's only review surface) overstates it.
- [x] green-frontend-api — `createGeneration(topic, documentType = DEFAULT_DOCUMENT_TYPE)` now maps via `WIRE_DOCUMENT_TYPE[documentType]`; `useGeneration.submit(topic, documentType?)` passes it straight through; the join lands in `useFlowNavigation.submitGeneration(topic)` = `generation.submit(topic, documentType ?? DEFAULT_DOCUMENT_TYPE)`, wired as `onSubmit={flow.submitGeneration}` in `DocumentGenerationFlow`. `ChatWorkspace`'s `(topic: string) => void` prop shape is untouched — the composer still only knows the topic, the type is joined in flow state where it lives. Removed the `it.skip` + the paired `@ts-expect-error` (self-removing as designed — leaving it was `TS2578`); no assertion touched. **Signature-shape decision — optional-with-default, AGAINST the preference red-frontend-api recorded:** a required parameter is a hard `TS2554` in nine one-argument call sites that all live in *test files* (`generationApi.test.ts` 29/51/71/83/96 + 4 `submit('тема')` calls across `useGeneration.test.ts`/`.resilience`/`.slowPoll`), which `tsc -b` compiles and which a green phase may not edit. The premortem's hazard is real but its proposed fix collides with tests-read-only, so it was closed the OTHER way the premortem named — the caller-level guard. Rationale recorded in a comment on `createGeneration`. **Caller-level guard (obligation 4, the point of the unit):** new `frontend/src/app/__tests__/useFlowNavigation.documentType.test.tsx` — `selectType('referat')` → `submitGeneration('Тема')` → asserts the `createGeneration` spy got `('Тема', 'referat')` exactly once. Uses `'referat'` deliberately, not `'doklad'`: with the default in place a `'doklad'` assertion would pass against the very hardcode it exists to rule out. Verified it bites — reverting `submitGeneration` to `generation.submit(topic)` fails it while every other test stays green (exactly the defect-survives-green scenario). Sits at the hook seam rather than click-driven because `referat` is `available: false` and not clickable in `TypeModal`. Suite **528 pass / 0 fail / 0 skip** (124 files; baseline 526 + un-skipped RED + new guard); `npm run typecheck` clean (run in the `-b` form per the recorded trap). All touched files under 200L (147/94/161/70). **Still open, NOT fixed here (out of green scope):** the auto-start caveat — `submitGeneration` only fires when the composer is used, so the `generation-generating` pending surface is still unreachable on load and **green-selenium 1.1 remains blocked**. This unit threads the type; it does not create a topic source. Owed to `align-design`, and there is still no red step after it to land an auto-start guard in. **Review passes on 21dff5a (refactor applied 1; agent-review CONCERNS/3; premortem CONCERNS/1 — both converge on the same gap):** (1) FIXED IN THIS UNIT — the guard stopped one line short of the defect. `DocumentGenerationFlow.tsx:104` (`onSubmit={flow.submitGeneration}`) is the ONLY production edge joining the thread-through to the UI, and nothing tested it: `useFlowNavigation.documentType.test.tsx` calls `submitGeneration` directly on the hook, so it never sees which callback the component hands down. Because both new parameters are optional-with-default, reverting that line to `flow.generation.submit` is NOT a type error (an optional trailing parameter stays structurally assignable to `ChatWorkspace`'s `onSubmit: (topic: string) => void`) and NOT a test failure — every card silently generates a `доклад` again with all 528 green. Verbatim the hazard the unit claimed to close. Closed with `frontend/src/app/__tests__/DocumentGenerationFlow.documentType.test.tsx` (53L): renders `App` with `generationApi`/`documentApi` mocked and drives the real UI (CTA → `type-card-doklad` → `topic-input` → `topic-send`), asserting `createGeneration` called exactly once with `(TOPIC, 'doklad')`. **Bite verified:** with line 104 reverted the test FAILS (`- "doklad"` / `+ undefined` as the 2nd arg); restored, it passes. (2) FIXED IN THIS UNIT — the `openDocumentFromHistory` comment claimed `documentType`'s `?? 'doklad'` fallback is "display text" for the breadcrumb LABEL only. False since this unit: `submitGeneration` reads the same field onto a POST. Not reachable today (the history path sets `mode='manual'` + `openDocumentId` → `ManualEditor`, and every route back to create passes through `selectType`), but the invariant was wrong in the file that has to know it. Comment corrected to state the new constraint for any future path into `step='form'`. (3) OWED, minor — `submitGeneration`'s `documentType ?? DEFAULT_DOCUMENT_TYPE` is a silent coercion. The branch is genuinely unreachable (`DocumentGenerationFlow.tsx:65` gates the workspace on `step === 'form' && documentType && mode`), but its stated purpose ("the composer cannot post a typeless request") is achieved by posting a *wrong-typed* request — the exact failure mode this unit exists to eliminate. If truly unreachable, not submitting (or throwing) fails loudly instead of billing a `доклад` nobody picked. No guard for either behaviour. Suite after all fixes: **529 pass / 0 fail / 0 skip** (125 files); typecheck clean.
- [x] align-design — **DECISION (user, 2026-07-28), resolves the block three units carried:** scenario 1.1's "picking a type goes straight to generation" means *the mode-select modal is gone* — the user lands directly on the topic composer and generation starts on send. It does NOT mean a POST fires at type-pick time. Story 01's own mockup `04-generation-form.html` always put topic entry AFTER the type pick (breadcrumb type chip → mode chip → "Новая генерация / Опишите, что нужно получить" → topic field), and story 18 removed only the modal, so today's `type → Composer → send` is faithful to that flow. **Consequence: the owed "auto-start generation" work is CANCELLED, not deferred — there is no topic source to design because the composer is the topic source.** `red-selenium` 1.1 must be relaxed before `green-selenium` can un-skip: it currently waits on `generation-generating` immediately after the type pick, which under this reading is wrong — it should assert the composer surface + no mode modal, and (per the earlier red-selenium note) that exactly one `POST /generations` fires on send. **DECISION 2 (user):** align against story 01's mockups rather than skipping — story 18 has no mockups of its own (Spec `[S]`), and the surfaces are story 01/05's. Drift found and fixed: the standalone form page was skipped by story 01 (known-debt #9) so its identity elements never landed anywhere — the idle screen had **zero** confirmation of which type was picked. Added `GenerationHeading.tsx`/`.css` (mockup 04 breadcrumb + title + subtitle, rendered only when `state === 'idle'`; the status badge owns the slot once a generation exists). Extracted `Composer.css` out of `ChatWorkspaceDoc.css` (which sat exactly at the 200-line cap → now 169) and corrected composer tokens to mockup 04 (padding `14px 16px` not `12px`, font `15px` not `14px`, focus border `--border-strong`, `::placeholder` color, submit row `14px 32px`/`15px`), added the required-marker and the `Обычно занимает 1–2 минуты` hint (which previously appeared only on the *pending* screen — the user was told the wait only after committing to it). **Breadcrumb decision:** dropped the mockup's *mode* chip, kept only the type chip — story 18 deleted the mode modal, so that chip could only render a hardcoded `Автоматический режим`, decorating a choice the user is never offered. Also NOT ported: mockup 04's `← Назад` (ChatWorkspace takes no back callback; wiring one is a behavior change, not alignment). Container stays at mockup 05's `1100px`/`40px` rather than 04's `1200px`/`48px` so the page does not jump width on submit. **/design-review FAILED first pass** — `Composer.tsx:22` hardcoded `Тема доклада` lifted from mockup 04, sitting five lines under a breadcrumb rendering the real picked type, so any non-доклад type showed two different type names on one screen; `aria-labelledby` made it the textarea's accessible name too, so a screen reader announced the wrong one. Fixed: new hand-written exhaustive `DOCUMENT_TYPE_GENITIVE` + `topicFieldLabel(documentType)` in `shared/documentTypes.ts` (genitive cannot be derived from `name` — доклад→доклада, эссе→эссе, сочинение→сочинения), `Composer` takes a `topicLabel` prop, `ChatWorkspace` takes `documentType` alongside `documentTypeLabel` (the shape `ManualEditor` already uses). New test asserts a `referat` render is named `Тема реферата`. **/design-review re-run PASS** — full mockup-04 text inventory re-diffed, zero surviving literals. Suite **530 pass / 0 fail / 0 skip**; typecheck clean; lint clean. Coverage on the focused set: `GenerationHeading` / `Composer` / `documentTypes` all 100%; one real gap recorded below. **OWED (non-gating, from /design-review):** `Composer.tsx` applies `cw-btn cw-btn-primary` but imports only `Composer.css` — those rules live in `ChatWorkspaceDoc.css` and it renders today only because `ChatWorkspace` happens to import that sheet. Invisible dependency; jsdom applies no CSS so no test catches it. Fix is NOT moving `cw-btn` into `Composer.css` (`DocArea` uses it too) but a small shared button stylesheet imported by each consumer. **OWED (repo-wide, pre-existing):** `lucide-react` is not installed despite the react-ts binding naming it, so all 6 icon sites render the generic `PlaceholderImage` square instead of real glyphs.
- [ ] red-frontend (coverage: blank topic on Ctrl+Enter does not submit)
- [ ] green-frontend (coverage: blank topic on Ctrl+Enter does not submit)
  - **Gap:** `ChatWorkspace.tsx:46` `if (trimmed) onSubmit(trimmed)` — false branch uncovered (file is 7/8 branches, 100% stmts/lines/fns). Reachable, not dead: the send *button* is `disabled={!topic.trim()}`, but `Composer`'s textarea `onKeyDown` fires `onSend` on Ctrl/Cmd+Enter with **no** disabled guard, so a whitespace-only topic reaches `send()` and must be swallowed. Untested today — deleting the `if` keeps all 530 green while letting an empty-topic POST through (backend 422).
  - **Pre-existing, not introduced by align-design.** `send()` is untouched by this unit's diff and the unit's test edits were purely additive (no test removed). Recorded here because the branch sits in the idle-composer path this unit reshaped (`Composer` now takes `topicLabel`, `send` is still its `onSend`), and it is one cheap renderer-level test.
- [ ] green-selenium
- [ ] demo

### Scenario 1.2: A generating document shows progress
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.1: A completed generation opens automatically in the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.2: The auto-transition fires the conversion exactly once
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.3: The editor is populated from the conversion response, not a re-read
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.1: The generated document is editable and saves
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: A failed generation shows a distinct error, not a perpetual spinner
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.2: A conversion error keeps the text and offers retry
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.3: A transient poll error shows a distinct error, not a spinner
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.4: A generation that never finishes stops at the client deadline
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: Leaving with unsaved edits is guarded
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: A blank document can still be started from scratch
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.2: The converted document appears in history
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
