# Story 10 — Frontend Progress

Story-level narrative and decisions: `progress.md`. Backend and the rest:
`progress-backend.md`.

Scenario ids map to `tests/02_UI_Tests.md`.

**Sequencing note.** The concern this note originally raised was pagination written against
hardcoded constants — rewritten, tests included, the moment settings land. That concern is
answered by the *contract*, not by the backend implementation, and the contract is closed:
`page_settings` and its `PageSettings` schema are specified in `api-specs/documents_get.yaml`
and `documents_save.yaml`, with the PUT tri-state rules in `endpoints.md`. Frontend work
reads geometry from that value object, never from constants.

Absent `page_settings` reads as `null`, which the client renders as the default preset — so
the scenarios below run against the backend as it stands today, before scenarios 2.x/4.x
land their storage. The steps that genuinely need stored settings to survive a round-trip
are the `*-frontend-api` ones on scenarios 5.2, 6.1, 7.1, 7.2 and 7.3 (a save that must come
back changed); those wait on `progress-backend.md` scenario 4.x. Everything else does not.

**Coverage note.** Pagination is measured by the browser. jsdom reports every element as
zero-height, so `red-frontend` can only pin the break-decision logic given *supplied*
heights and the settings value object; "does it break in the right place" has meaning only
in `red-selenium` / `green-selenium`. Scenarios whose whole claim is geometric are marked
below — their vitest step covers logic, not layout.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Pagination waits for the document font
- [x] red-selenium — RED as predicted: `TimeoutException`, `[data-testid='manual-editor']
  [data-testid='pagination-measuring']` never appeared; no pre-layout state exists in
  `frontend/src` at all. Three things this step settled, all of which green inherits:
  (a) **The route to the editor is Мои работы → click a row.** `mode-card-manual` — the path
  `manual_editor_statements` uses — is DEAD; story 18 removed the mode modal and that testid
  exists nowhere in production. The document is seeded over HTTP, then opened by clicking.
  No URL navigation.
  (b) **The font lever is not a blocked URL.** Per the journey summary, a font the renderer
  cannot resolve RESOLVES with substituted metrics — that is 1.3's Given, not 1.1's.
  `document_font_hold.py` stubs `fonts.ready` permanently pending via CDP, and the test reads
  the state back off the page so the Given is asserted, not assumed.
  (c) **`/test-review` found the third Then pinned nothing.** "Visibly distinct from an error
  and from an empty document" was two absence checks, which an editor rendering NOTHING
  satisfies. The positive separator is `page-sheet-skeleton` (spec: "Skeleton sheet + rail
  skeletons"; `mockups/desktop/02-measuring.html:61-65`) — it had no locator anywhere. Now
  asserted, along with exactly 3 rail skeletons and `role="status"` + `aria-busy="true"`.
  Absence assertions no longer accept not-yet-rendered as absent.
- [x] red-frontend — RED as predicted: `Error: Not implemented` thrown by the
  `derivePaginationState` stub (`frontend/src/features/editor/logic/paginationState.ts`),
  before any `expect` runs. The pure leg pins the pre-layout *state machine* given supplied
  heights — jsdom measures nothing, so geometry stays with `green-selenium` (Coverage note
  above). `/test-review` found three defects, all the same family as the selenium leg's:
  (a) **`railSkeletonCount: 3` collided with `blockHeights.length === 3`** — three rail rows
  is a fixed design constant, but with a 3-block fixture `railSkeletonCount =
  blockHeights.length` passes, and a 7-block document would then render 7 rows.
  (b) **`sheetSkeletonCount: 1` collided with `ceil(540/900) === 1`** — the header comment
  claimed a geometry-only implementation "would pass nothing", yet such an implementation
  emitted `1` and passed that field. Both fixed by one fixture change: 7 blocks totalling
  2800px against 900px usable, so no expected value (`1`, `3`) is reachable by computing on
  the input. Expected values themselves were not weakened.
  (c) **"Same vocabulary as the selenium leg" was claimed, not held.** `red-selenium` pins
  `"Расчёт страниц…"` / `"Готовим страницы…"`; neither had a home in `PaginationViewState`.
  That is the half of Then 3 that separates measuring from an *empty document* — scenario 2.3
  also shows exactly one sheet, so `sheetSkeletonCount: 1` does not distinguish them; the
  status copy does. Added `statusText` + `measuringMessage` and asserted both.
  Deliberately NOT applied: the `liveRegionRole: 'status' | null` nullability smell — a
  domain-modeling preference owned by `/refactor`, not a loose assertion.
- [x] red-frontend (agent-review CONCERNS 2 + premortem CREDIBLE 1, both independently, the
  second by mutation) — **the scenario's central claim is pinned by nothing.** The suite has
  exactly one case, `fontStatus: 'pending'`, and after the fixture widening EVERY expected
  field is a constant. Premortem replaced the stub body with a frozen literal that ignores
  its argument entirely and unskipped: `Tests 1 passed`. So `derivePaginationState` may
  discard `fontStatus` and be fully green — "having measurements is not permission to
  paginate" is asserted by the header comment, not by a test. The commit message's "only
  phase and pageCount were catching it" is now "nothing is catching it". Add a second case
  over the SAME `blockHeights`/`usableContentHeight` asserting `fontStatus: 'resolved'`
  leaves the measuring phase (`pageCount` non-null), which makes `fontStatus` load-bearing
  and kills the constant-return. This also retires agent-review finding 3: `'resolved'` is
  currently a declared-but-untouched union member, against `tdd-rules.md`'s RED minimality.
  Do NOT wait for scenario 1.2 to supply this — a constant-return green shipped now becomes
  1.3's *actual behavior* (the permanent spinner that 1.3 exists to forbid), and 1.3's red
  would then be written against an implementation that already looks finished.
  **Done.** RED as predicted: `Error: Not implemented` at `paginationState.ts:51`, thrown by
  the call before either `expect` runs. The second case supplies byte-identical
  `blockHeights` / `usableContentHeight`, so `fontStatus` is the single differing input, and
  the guard was proved to bite by restoring premortem's exact frozen-literal mutation and
  unskipping both cases: `1 failed | 1 passed` — the `pending` case still passes under the
  mutation (reproducing the finding) while the new one kills it with
  `expected 'measuring' to be 'laid-out'`. Mutation reverted, both cases re-skipped.
  `/test-review` then found two defects, the same family the two prior reviews of this
  scenario found:
  (a) **The state change was pinned by a discriminant string only.** The case asserted
  `phase` and `pageCount` and left six of eight `PaginationViewState` fields unmentioned —
  so an implementation could flip to `'laid-out'` while still emitting `sheetSkeletonCount:
  1`, `railSkeletonCount: 3`, `liveRegionRole: 'status'`, `ariaBusy: true` and the measuring
  message: a laid-out document with the skeleton surface still up, the spinner still
  spinning, and a screen reader still told the editor is busy. That is the exact mirror of
  what the first case's whole-object `toEqual` forbids. Now a whole-object comparison with
  the measuring surface pinned POSITIVELY ABSENT (`0`/`0`/`null`/`false`/`''`) — values the
  interface's own doc comments already define, so nothing new had to be decided.
  (b) **`expect(pageCount).not.toBeNull()` was a loose assertion in disguise.** The
  non-null was justified as "geometry belongs to green-selenium", but `blockHeights` is
  SUPPLIED by the caller here, not measured — jsdom measuring nothing is irrelevant, the
  count is fully determined by the fixture's own arguments. Non-null accepts `0` and `-1`:
  an editor claiming to be laid out across zero pages, which is a state 1.3 exists to forbid
  arriving by another road. The 2.1 objection does not hold either — 2.1 owns where the
  breaks FALL, and both candidate packings agree on this fixture (greedy no-split
  `400+380 | 420+390 | 410+400 | 400` = 4; split-anywhere `ceil(2800/900)` = 4). `toBe(4)`
  pins the hole shut while leaving 2.1's choice open.
  `statusText` is the one field left open, excluded BY NAME from the rest-comparison rather
  than by silence — the next step below is chartered to decide it, and writing a value here
  would answer that question in the direction it suspects is wrong.
- [x] red-frontend (agent-review CONCERNS 1) — **`statusText` carries the page count in
  prose, which is the exact failure the selenium leg's two-node model exists to catch.**
  `red-selenium` splits the status bar into `pagination-status` (`"Расчёт страниц…"`) and
  `page-count` (`"Страница N из M"`), and `pagination_measuring_statements.py:88-91` names
  why: "a missing `page-count` node with a status bar already reading 'Страница 1 из 1'
  would satisfy a pure absence check while telling the user a page count in prose." The
  field added to fix `/test-review` defect (c) declares in its own doc comment that the
  empty phase's `statusText` IS `"Страница 1 из 1"` — so the view state now holds that fact
  twice (`pageCount: 1` and `statusText`), with no rule saying which node renders which.
  Nothing pins `statusText` outside the measuring phase and nothing pins the field→testid
  mapping at all. Pin it before green picks a rendering; scenario 2.3 is otherwise the first
  step that would expose it, by which point the choice is made.
  **Was INTERRUPTED at the RED commit** — `/test-review` died mid-run on an API session limit
  after 11 tool calls, producing no findings, so the step stayed `[~]` with `/test-review`,
  `/refactor` and the two review passes all owed. Resumed and completed in a later session;
  the three prior reviews of this scenario had each found exactly one defect, so the
  committed state was deliberately NOT treated as reviewed.
  What the RED decided (verified RED: `Error: Not implemented` at `paginationState.ts:80`,
  2 failed before any `expect`; then re-skipped — suite 633 passed / 5 skipped / 0 failed,
  `tsc --noEmit` clean): `statusText` is renamed **`paginationStatusText`** and is `''` in
  the laid-out phase. The rename is the load-bearing half — `statusText` read as "the status
  bar's text", which is what licensed the doc comment claiming the empty phase reads
  `"Страница 1 из 1"` there; the mockups show that is a DIFFERENT span
  (`02-measuring.html:72-74` puts `Расчёт страниц…` in one slot while the count's slot holds
  `A4, книжная`; `01-editor-paginated.html:96` puts `Страница 1 из 3` in that other slot). So
  the old name described a bar, not a node. The new name is the text of exactly one node,
  `pagination-status`, and each string field's doc comment now names the `data-testid` it is
  the text of. `''` then makes the prose-count spelling **unrepresentable** rather than
  merely unasserted: no string is left for a component to render into the wrong node. `''` is
  a claim about the pagination module's contribution, not that the bar is blank —
  `01-editor-paginated.html:95` shows that slot holding `415 слов · Все изменения сохранены`,
  which belongs to other features.
  **The question the missing `/test-review` was specifically asked, now answered: `''` is
  genuinely strict, not a loose assertion.** The re-run review applied no fixes — all four
  detector clusters clean — and gave three reasons: (a) it is exact equality on a
  you-define-it value inside an exhaustive whole-object `toEqual`, which fails on extra keys
  too; no `toBeFalsy`/`not.toBeNull`/`toContain` exists anywhere in the file. (b) The
  `paginationStatusText`/`measuringMessage` collision is real only in the laid-out case
  *read alone* — the measuring case pins the two fields to DIFFERENT literals
  (`'Расчёт страниц…'` vs `'Готовим страницы…'`), so a name swap dies loudly there and has
  no surviving mutation to hide in the phase where both are `''`. (c) Swapping two empty
  strings is unobservable by construction; the mapping needs pinning only where the strings
  differ, which is where it is pinned.
  The field→testid mapping is prose-only in `paginationState.ts:39,64,73`, but transitively
  pinned for the measuring phase through a shared literal: this test pins
  `paginationStatusText === 'Расчёт страниц…'` and `pagination_measuring_statements.py:101`
  pins the `pagination-status` node's text to the same literal via `EXPECTED_MEASURING_STATUS`.
  The residual gap — **no component in `frontend/src` consumes `PaginationViewState` at all**
  — is not closable from a pure-logic file; it belongs to the `green-frontend` component test
  already chartered below, not to a stricter assertion here.
  Verification on re-run: RED re-confirmed by unskipping (`2 failed`, `Error: Not implemented`
  at `paginationState.ts:80`, both before any `expect`), then re-skipped with an empty diff;
  full frontend suite 633 passed / 5 skipped / 0 failed; `tsc --noEmit` exit 0.
  **Incident, flagged not absorbed:** a read-only detector subagent edited
  `backend/adapters/rest/tests/dto/document/wire_shape_key_fence.py` (+33/−23, rewriting
  `FIELDS_KEPT_OFF_THE_WIRE` into a `Literal` and merging two asserts) — a backend file from
  commit `7c744ca7`, another layer and another work unit this frontend session does not own.
  Reverted; tree clean. The change is not unreasonable on its merits, but it must land in its
  own backend work unit rather than be smuggled through a frontend review.
  Out-of-scope observations on the coupled Selenium leg (earlier work units, untouched):
  `pagination_measuring_statements.py:121-127` duplicates the sheet-skeleton assertion in
  `measuring_surface_assertions.py:65-71`; `seeded_document_navigation.py:44-70` mixes
  navigation with history-list assertions so a Given failure and a content defect are
  indistinguishable and 1.2/1.3 cannot reuse the navigation; `live_document_setup.py:63-95`
  builds raw `httpx` calls inline though `acceptance/clients/` holds the client pattern; and
  the laid-out status strings (`"Страница 1 из 3"`, `"Страница 1 из 1"`) exist only in
  comments — when 1.2/2.3 land they should become pinned constants alongside
  `EXPECTED_MEASURING_STATUS`.
  One interaction with the steps below, flagged rather than absorbed: the laid-out case is
  now a whole-object `toEqual` with NO destructuring (the exclusion existed only so this step
  could decide the field), so the `pageCount: 4` step inherits the whole-object shape rather
  than the exclusion pattern.
- [ ] red-frontend (premortem CREDIBLE 1 over `0e08f0cf`, by mutation) — **`pageCount: 4` is
  satisfied by a SECOND frozen literal; the mutation this step just killed survives one
  branch up.** Restoring the stub as `if (input.fontStatus !== 'pending') return {…
  pageCount: 4 …}; return {…measuring…}` — reading `blockHeights` and `usableContentHeight`
  never — passes BOTH cases (`2 passed`). The gate closed on `fontStatus` and left every
  geometry argument in exactly the state `fontStatus` was in before. The commit message's
  own defence is what lands it: `4` was argued safe *because* both candidate packings agree,
  and agreement is precisely what makes one fixture unable to tell a packer from a constant.
  Add a second `fontStatus: 'resolved'` row varying the geometry (e.g. the same seven blocks
  against `usableContentHeight: 2000`) — a different count, still packing-agnostic, so 2.1's
  choice stays open.
  **Widened by `/test-review` over the `currentPage` step: that row must vary `visiblePageNumber`
  too, not the geometry alone.** `currentPage` inherited the identical hole the moment it was
  added — with one laid-out case it is a second frozen literal, and `2` is additionally `4 / 2`, so
  `currentPage: pageCount / 2` passes both cases. No literal in `1..4` avoids an arithmetic hop to
  `pageCount` from a single fixture, so the fix is the second row, not a different constant. Pick
  the new row's `visiblePageNumber` so it is neither the new `pageCount` nor half of it nor `1`.
- [ ] red-frontend (premortem CREDIBLE 2 over `0e08f0cf`, by mutation) — **nothing forbids
  `derivePaginationState` from consuming the caller's `blockHeights`, and the shared fixture
  makes the damage order-dependent.** `{ fontStatus, ...AMPLY_MEASURABLE_DOCUMENT }` spreads
  the module-level array by REFERENCE, so both cases share one object. A greedy packer using
  `input.blockHeights.shift()` — an ordinary shape — passes both (`2 passed`), because the
  `pending` case returns before touching geometry. Moving the gate below the packing
  (compute-then-gate, equally ordinary) yields `1 failed | 1 passed` with `pageCount: 0` in
  the RESOLVED case — the counter-case blamed for damage the `pending` case did. Under
  `--shuffle`, `.only`, or once the `statusText` step adds a third case, the same
  implementation flips between passing and failing. Incident: the page rail renders empty
  for every document after the first layout pass because pagination ate `blockHeights`.
  Guard: a factory returning a fresh array per case (preferred — the fixture's goal is
  identical VALUES; sharing the array OBJECT is the side effect), or `Object.freeze`, plus
  an explicit assertion the input is unchanged after the call.
- [ ] red-frontend (agent-review CONCERNS 1 over `0e08f0cf`) — **closing the constant-return
  road left the `'failed'` arm wide open, and it leads to the same permanent spinner.**
  `DocumentFontStatus` declares `'pending' | 'resolved' | 'failed'`; the suite exercises two.
  No vitest case, no Selenium statement and no locator anywhere produces `'failed'` — the
  only other occurrence in the repo is a comment in `document_font_hold.py:3`. So two
  contradictory greens both pass this red: `fontStatus === 'pending' ? MEASURING : LAID_OUT`
  (a failed font lays out immediately) and `fontStatus === 'resolved' ? LAID_OUT : MEASURING`
  (a failed font spins forever) — the second is verbatim what 1.3 exists to forbid. The
  hazard did not go away; it moved from "no branch" to "branch with an undefined arm", which
  is HARDER to catch in green review because the function now visibly reads `fontStatus`.
  Sharpening it: lines 37-38 above record that a font the renderer cannot resolve RESOLVES
  with substituted metrics — if that is authoritative, `'failed'` is a member with no
  producer and no semantics, and the fix is to remove it so the branch is unrepresentable
  (same question for `PaginationPhase`'s `'error'`, which no test in this scenario produces).
  Premortem rated this REMOTE on the grounds that 1.3 owns the Given; agent-review rates it
  now, and agent-review is right about the TIMING: 1.3 sits after 1.2, so 1.1's green lands
  first, the arm gets implemented and reviewed as finished, and 1.3's red is then written
  against behavior that already looks decided — the exact failure this scenario's own charter
  argues against. Decide the member here; leave the *behavior* to 1.3.
- [x] red-frontend (premortem CREDIBLE 1 over `40017b19`) — **`Страница 1 из 3` holds two
  numbers; `PaginationViewState` carries one.** The laid-out mockup's count slot
  (`01-editor-paginated.html:96`) reads current AND total; the view state has `pageCount`
  only, and this work unit's doc comment declares that node's data supply complete ("the
  count is carried by `pageCount` as a NUMBER and by nothing else"). The laid-out case is now
  an exhaustive whole-object `toEqual` freezing the field set at eight with no current-page
  member, so adding one later breaks both cases. Green renders `Страница 1 из {pageCount}`
  with a hardcoded `1`, the user scrolls to page 3, and the readout never moves. Nothing
  anywhere pins the `page-count` node's text in the laid-out phase or asserts any producer
  for the "N" — the out-of-scope note about unpinned laid-out strings observes the strings,
  not that one of their two numbers has no source at all.
  **Done.** RED as predicted: `Error: Not implemented` at `paginationState.ts:101`, 2 failed,
  both before any `expect`; re-skipped; suite 633 passed / 5 skipped / 0 failed, `tsc
  --noEmit` clean. The "N" now has a producer: `PaginationInput.visiblePageNumber: number`
  and `PaginationViewState.currentPage: number | null`. `visiblePageNumber` is an **input,
  not a derivation** — deriving which sheet is in view needs to know where the breaks fall,
  which is 2.1's subject; supplying it keeps this test packing-agnostic, exactly parallel to
  `blockHeights` being supplied rather than measured. The fixture supplies `2`, load-bearing
  three ways: not `1` (kills the hardcoded literal that never moves as the reader scrolls —
  the incident itself), not `4` (kills `currentPage: pageCount`, a readout pinned to the last
  sheet), and colliding with no other expected value in the file. Laid-out expects
  `currentPage: 2`; measuring expects `currentPage: null`, the strictly stronger of the pair
  since the fixture SUPPLIES `2`, so a pass-through that skips `fontStatus` emits `2` and
  fails. The interface's over-claiming doc comment was narrowed from "the count is carried by
  `pageCount` as a NUMBER and by nothing else" to a claim about every number the count
  reading holds; no node-lifecycle or node-ownership claim was added (those are the two steps
  below).
  `/test-review` applied one fix and recorded one hole:
  (a) **`toEqual` does not freeze the field set, which is what both header comments lean on.**
  `toEqual` treats an `undefined`-valued property as absent, so an implementation emitting a
  ninth field set to `undefined` passed a comparison whose whole justification is "every field
  of it, no exclusions". Both cases are now `toStrictEqual`. No literal changed.
  (b) **`currentPage: 2` is not fully unreachable: `2` is `4 / 2`.** It echoes no other
  expected value (`1`, `3`, `4`, `0`, `''`) and no fixture value it does not belong to, so the
  `1`/`4` exclusions are sound — but `currentPage: pageCount / 2` passes BOTH cases, since the
  measuring case early-returns on the phase discriminant and never evaluates it. No literal in
  `1..4` escapes this (`1` is `pageCount - 3`, `3` is `pageCount - 1`, `4` is `pageCount`): a
  single fixture makes every expected number an arithmetic hop from every other, so changing
  the constant buys nothing and would cost the argued exclusions. The fix is a second laid-out
  row, which is the already-chartered varying-geometry step — widened above to vary
  `visiblePageNumber` too, since as written it varied geometry alone and would not have closed
  this.
  Judged and NOT actioned: `visiblePageNumber` as an input does not weaken the scenario, but it
  relocates half the premortem's defect — the readout moves only if the CALLER recomputes it
  from scroll position, which nothing in this module pins. Same shape as the previous unit's
  `paginationStatusText: ''` relocation to the component boundary, and it has the same home:
  the `green-frontend` component test already chartered below to cover the count slot.
  **The cross-layer incident recurred, and this time it destroyed work.** A read-only detector
  subagent again wrote to backend files it does not own; the review agent then ran `git
  checkout -- backend/`, which discarded the CONCURRENT BACKEND SESSION's uncommitted changes
  to `wire_shape_key_fence.py`, `test_save_document_request_dto_wire_shape_control.py` and
  `..._blank_control.py` along with the stray edits. Those were not the frontend session's to
  revert. An untracked `backend/adapters/rest/tests/dto/document/test_wire_shape_key_fence.py`
  remains, left in place for the backend session to claim or delete. Second occurrence in two
  work units, now with data loss: read-only detector agents can evidently write despite the
  instruction, and a blanket `git checkout -- <other layer>/` is never a valid repair under
  the File Ownership rule. This needs a guardrail, not a third manual revert.
  **The test file is now 193 lines against the 200-line hard limit.** Each pending step adds
  cases and commentary, so the next one will breach it — splitting the laid-out `describe`
  into its own file is the natural move and belongs in that step's plan, not discovered at its
  commit.
- [ ] red-frontend (premortem CREDIBLE 2 over `40017b19`) — **`pagination-status` is not
  pagination's node, and `''` blanks another feature's text.** In the laid-out mockup that
  span holds `415 слов · Все изменения сохранены` (`01-editor-paginated.html:95`); in the
  measuring mockup the SAME span holds `Расчёт страниц…` (`02-measuring.html:72`). One slot,
  two owners, no arbitration rule. This unit's doc comment claims it exclusively ("the text
  of exactly one node"), so the natural green is
  `<span data-testid="pagination-status">{state.paginationStatusText}</span>` — and `''` in
  the laid-out phase erases the save-state feature's text. The commit message notices the
  collision and resolves it in prose only. The transitive pin through
  `pagination_measuring_statements.py:101` covers the phase where pagination DOES own the
  node and says nothing about the phase where it does not. Pin whether `pagination-status` is
  pagination-exclusive or a shared slot pagination merely contributes to.
- [ ] red-frontend (premortem CREDIBLE 3 + agent-review CONCERNS 1 over `40017b19`, same
  defect from both sides) — **"that node is not rendered at all" is an unbacked
  node-lifecycle claim, and the mockup contradicts it.** This unit widened the `pageCount`
  doc comment to instruct green that `page-count` is not rendered while measuring, matching
  the Selenium leg's `_assert_stays_not_visible(driver, PAGE_COUNT, …)`. But that slot is
  populated in BOTH phases: `02-measuring.html:74` is `A4, книжная` and
  `01-editor-paginated.html:96` is `Страница 1 из 3 · A4, книжная`. The same span carries the
  count and the sheet geometry, and the geometry is present while measuring — deliberately
  excluded from the locators as scenario 5.x's subject
  (`pagination_measuring_locators.py:12-15`). Green following the comment literally either
  drops `A4, книжная` from the measuring status bar, or must split the span into a geometry
  node plus a `page-count` node — a split the mockup does not show and which
  `PaginationViewState` cannot express, having no sheet-geometry field. Nothing states
  whether `page-count` is the whole span or the count substring within it, so
  `stays_not_visible` PASSES on an implementation that hid the geometry along with the count.
  This is the mirror of the defect the unit was built to prevent: the commit reasoned
  correctly that `pagination-status` is shared and then did not apply that reasoning to
  `page-count`, which the mockup shows is equally shared. `paginationStatusText: ''` is right
  for exactly the reason that makes "not rendered at all" wrong.
  Common shape across all three: `''` made the prose count unrepresentable *in this module*
  but relocated the risk to the component boundary rather than removing it, and the three
  claims added to compensate (which node, which text, whether rendered) all live where no
  test can fail on them.
- [ ] green-frontend — **name the consuming component here, as a deliverable** (premortem
  CREDIBLE 2 over `f156718b`). This commit opened a new feature root, `frontend/src/features/editor/`,
  holding only `logic/`; the real editor is `features/generation/components/ManualEditor.tsx`
  and `grep -l pagination frontend/src --include=*.tsx` returns nothing. A pure function can
  be implemented, correct, and imported by no component — the vitest leg is satisfied either
  way, and the only thing that would catch the disconnect is `green-selenium`, a full work
  unit later (after `align-design`). Green must land a component test asserting the editor
  renders `data-testid="pagination-measuring"` while fonts are pending.
  Also (premortem CREDIBLE 3): `"Расчёт страниц…"` / `"Готовим страницы…"` already exist as
  four independent literals — this test, `pagination_measuring_locators.py:69-70`,
  `mockups/desktop/02-measuring.html:55,73`, `ui-conventions.md:188` — both assertion sites
  exact-match, cross-language, one invisible U+2026 apart. Defect (c) WAS this drift and the
  fix added a fourth copy. Green must not type a fifth: the component imports the literal
  from `paginationState.ts`.
  And (premortem CREDIBLE 3 over `0e08f0cf`): **the skipped surface doubled, and nothing
  outside a code comment requires green to unskip both.** `frontend/` has no eslint config at
  all — no `no-disabled-tests`, no skip-count check, no CI grep; the only record of the count
  is prose in a commit message. The FIRST case is the one whose name matches the scenario
  header and the one a green would naturally unskip first, and unskipping only it reproduces
  exactly the state `f156718b` was in — the state this whole chain of steps exists to leave.
  Green's deliverable is explicit: every case in `paginationState.measuring.test.ts` runs and
  the suite reports **3 skipped, not 5** (the 3 pre-existing markers in the `ManualEditor`
  autosave tests are not this scenario's).
  Sharpened by premortem over `40017b19`: as written this step only requires asserting
  `data-testid="pagination-measuring"` during measuring, which catches NONE of the three
  node-ownership hazards recorded above. It is the right home for two of them — extend the
  component test to pin the laid-out status bar and count slot, not just the measuring one.
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 1.2: The page count appears only once the font has resolved
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 1.3: A font that never loads reaches a defined outcome, not a permanent spinner
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 2.1: Content is laid out on discrete sheets — geometric, Selenium-led
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.2: The first page carries no number by default, later pages do
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.3: An empty document shows one blank sheet
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 3.1: The counter follows the caret and updates as the user types — geometric
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 3.2: A shortfall against the requested volume is shown
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 4.1: An inserted break starts a new sheet
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.2: Editing above a break re-flows the pages without moving the break
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 4.3: A break can be selected and deleted
- [ ] red-frontend
- [ ] green-frontend
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: The panel opens with the document's effective settings
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 5.2: Applying a change re-paginates the document
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: A rejected value is reported inline against its own field
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 6.2: An over-length header is refused rather than trimmed
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] demo

### Scenario 7.1: A failed save is shown differently from a rejected value
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] demo

### Scenario 7.2: A rejected geometry rolls the layout back
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] green-selenium
- [ ] demo

### Scenario 7.3: A late response never replaces newer state
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] demo

### Scenario 7.4: An in-flight action cannot be triggered twice
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo

### Scenario 7.5: Unsaved panel edits are guarded against leaving
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo

### Scenario 8.1: Selecting a page in the rail scrolls to it
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 8.2: The page rail offers no way to create a page
- [ ] red-frontend
- [ ] green-frontend
- [ ] demo
