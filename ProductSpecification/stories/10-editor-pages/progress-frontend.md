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

**CONCURRENT-SESSION WARNING (observed 2026-08-10, during the `designNumbers` unit).** A second
session is editing THIS layer's files, not just `backend/`. While `/refactor` ran over `36574438` it
observed `laidOutRows.fixture.ts:144` holding `NO_SKELETONS = 9` uncommitted — the exact mutant
`designNumbers.test.ts` names as the one that used to survive — and `FONT_GATE_ROW`'s geometry
retuned to derive `8`; both reverted themselves mid-run, so that run's single failure was a race
against a live mutation, not a real failure. `paginationState.crossRow.test.ts` then grew 142 → 153
and landed as commit `c2d76b3d` ("a uniqueness check was never the constants' guard") ON TOP of
`36574438` — the same finding this unit was executing, done twice in parallel. The File Ownership
rule assumes one session per LAYER; two frontend sessions on one story breaks it. This session
reverted nothing. Before resuming, confirm only one frontend session is running.

**Flake note (observed 2026-08-09, over `72d9b438`).** `ManualEditor.autosaveDirtyGuardRevertedEdit.test.tsx:69`
(`expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)`, with the `DIRTY_STATUS` assertion
at :73) failed once and then passed on two subsequent runs of byte-identical, unmodified code —
`1 failed | 632 passed`, then 633 twice. Autosave timing, not a regression, and not this story's
file. It will intermittently redden the suite for whoever runs it next; do not chase it as a
pagination failure.

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
- [x] red-frontend (premortem CREDIBLE 1 over `0e08f0cf`, by mutation) — **`pageCount: 4` is
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
  **This step also owns the file split.** `/refactor` over `72d9b438` declined to split the
  193-line test file and argued the seam belongs here: 193 does not exceed 200, so there is no
  violation to fix yet; this step dissolves the current structure anyway (a second laid-out row
  means `AMPLY_MEASURABLE_DOCUMENT` stops being the single binding every case is driven over),
  so "split the laid-out `describe` out" is a good seam for the file as it stands today and a
  poor one for the file this step produces; and splitting now would put the counter-case's
  load-bearing co-location — both cases and the shared binding on one screen, which is what
  kills the frozen-literal implementation — behind a cross-file import. This step both breaches
  200 and knows where the new seam is, so it pays the cost exactly when it buys something.
  **Done.** RED as predicted: `Error: Not implemented` at `paginationState.ts:101`, 3 failed
  (all three cases), none reaching an `expect`; re-skipped; suite 633 passed / 6 skipped / 0
  failed, `tsc --noEmit` clean. The new row: 11 blocks totalling 3600px against
  `usableContentHeight: 600`, `visiblePageNumber: 5` → `pageCount: 6`, `currentPage: 5`.
  **Both mutations died on the new row alone**, each `1 failed | 2 passed` — the two old cases
  still passing, which reproduces the premortem finding verbatim: (1) the frozen literal one
  branch up (`if (fontStatus !== 'pending') return {…pageCount: 4, currentPage: 2…}`, reading
  no geometry) and (2) `currentPage: pageCount / 2` over a real `ceil(sum/usable)` packer
  (`- 5, + 3`). Both reverted; `paginationState.ts` byte-identical.
  **The split, by SUBJECT rather than by phase.** `paginationState.measuring.test.ts` (192
  lines) keeps BOTH font-gate cases over the single `AMPLY_MEASURABLE_DOCUMENT` binding —
  that co-location is what kills the discard-the-argument mutation, so it had to stay intact.
  The varied-geometry row is exactly the case that would have dissolved "one shared binding",
  so it is what leaves, into `paginationState.laidOut.test.ts` (80 lines). Cross-references
  run both ways so neither file orphans the other's context.
  `/test-review` verified the two claims the row rests on and found one gap:
  (a) **Packing-agnosticism verified independently and it is stronger than argued.** Greedy
  no-split, first-fit (later block backfilling an earlier gap), best-fit-decreasing and
  `ceil(3600/600)` all answer 6. `ceil` is the theoretical lower bound and greedy ACHIEVES it,
  so no packer can answer below 6 and none of the plausible ones answers above. A widow/orphan
  rule is not expressible over this input at all — `blockHeights` carries no semantics to
  keep-with-next on. Bounded residual, not a defect: the exactness that creates the
  agnosticism means a packer reserving slack would break to 7, but `usableContentHeight` is
  already the post-margin figure, so no such packer can be written against this contract.
  (b) **`5` is `6 − 1`, so `currentPage: pageCount - 1` passes this row on its own** — the
  0-based/1-based off-by-one, by some distance the likeliest of the three accidents, and the
  one the header's exclusion list omitted while reading as exhaustive. It IS killed, but only
  by the sibling file's row (`4 − 1 = 3` against expected `2`). Pre-split a reader saw both
  rows at once; post-split the laidOut file made a completeness claim it could no longer back.
  No mutation survives both rows (the only `f` with `f(4)=2, f(6)=5` is `1.5p − 4`, which
  nobody writes). Fixed comment-only: the exclusion paragraph now names the hop and attributes
  its kill to the sibling row.
  Flagged, not fixed: the measuring file has **8 lines of headroom**, and its header is where
  the pending `'failed'` arm and shared-`blockHeights` guard would naturally document
  themselves. Those steps will likely force a further split — follow the subject-seam
  precedent set here.
- [x] red-frontend (premortem CREDIBLE 2 + agent-review CONCERNS 1 over `2572b8be`, the same
  defect from both sides) — **the cross-row kill of `currentPage: pageCount - 1` is held by
  prose in two headers and by nothing executable, and the fixture that holds it is already
  chartered to be edited.** `laidOut.test.ts` is explicit that the hop dies only across the
  pair: `4 - 1` is `3` against the measuring file's expected `2`. That binding is a COMMENT.
  `AMPLY_MEASURABLE_DOCUMENT.visiblePageNumber = 2` against `pageCount: 4` is the entire kill,
  and the pending shared-`blockHeights` step, the `'failed'` arm and the predicted further
  split all land in that file. Retune it to `visiblePageNumber: 3` — or to
  `usableContentHeight: 600` — and `p - 1` becomes live across both rows with **zero tests red
  anywhere** and no comment flagged stale. The reader making that edit is in the measuring
  file, whose header calls it "the FONT GATE" and never says its `2` is load-bearing for a
  different file's exclusion: the cross-reference points FORWARD for the seam, not BACKWARD for
  this dependency, so "cross-references run both ways" is true of the seam and false of the
  kill. A pre-split reader saw both rows on one screen; nothing does now. This is NOT the
  shared-`blockHeights` finding below — that one is the production function mutating a caller's
  array; this is the fixture's NUMBERS being a silent cross-file invariant. Guard: hoist both
  laid-out rows' `(pageCount, currentPage)` pairs into one shared fixture module both files
  import, so editing either is visibly editing the pair — or at minimum add the reciprocal
  warning to `AMPLY_MEASURABLE_DOCUMENT`'s header naming what its `2` kills and where.
  **Done, taking (a) AND (b)** — (b) alone would have re-committed the original error one file
  over, since the finding is precisely that prose does not fail. Two new files:
  `laidOutRows.fixture.ts` (80 lines) holds `FONT_GATE_ROW {pageCount: 4, currentPage: 2}`,
  `VARIED_GEOMETRY_ROW {pageCount: 6, currentPage: 5}` and `RULED_OUT_CURRENT_PAGE_HOPS`
  (`pageCount`, `pageCount - 1`, `pageCount / 2`, `1`) as an executable table, with the
  rationale for both numbers moved to where the numbers now live;
  `paginationState.crossRow.test.ts` (66 lines after `/test-review`'s second case) is **LIVE,
  not skipped** — it never calls
  `derivePaginationState`, it checks the fixtures, so it runs today against the unimplemented
  stub. It pins the refutation matrix BY NAME (`pageCount - 1` → `[font-gate]`, `pageCount / 2`
  → `[varied-geometry]`, `pageCount` and `1` → both), because a weaker "at least one row
  refutes each hop" stays green while the kills MIGRATE between rows, and migration is the
  failure mode. Both test files now derive `visiblePageNumber` from their row's `currentPage`,
  so the supplied viewport and the expected readout can no longer drift apart — the
  pass-through pin is mechanical instead of a coincidence of two literals. **Co-location
  intact:** `AMPLY_MEASURABLE_DOCUMENT` is still one binding driving both font-gate cases; only
  the number is shared, not the geometry.
  RED as predicted on every row: unskipped → 3 failed, all `Error: Not implemented` at
  `paginationState.ts:101:9`, none reaching an `expect`, with crossRow green alongside.
  **Mutation 1** (`currentPage: pageCount - 1` over a real packer): `1 failed | 3 passed`,
  killed by the font-gate row only. **Mutation 2** (retune `FONT_GATE_ROW.currentPage` to `3`
  so the rows agree under `p - 1`): `1 failed | 3 skipped` — the headline, since it fires with
  every stub case still skipped, in the exact state where today nothing fails at all.
  `/test-review` found one real defect and answered the three judgement calls:
  (a) **The matrix admitted `[]`.** It is not a tautology — `rowsRefuting` computes
  `hop.derive(row.pageCount) !== row.currentPage` from the fixture constants and compares
  against an independent literal — but retuning the font-gate row to `3` made the computed
  entry `'pageCount - 1': []`, and green was then one token away, in a matrix whose own title
  still read "each by a named row". A fixture edit satisfiable by a matrix edit in the same
  obvious motion. Added a second live case asserting non-emptiness as a COMPUTED property: the
  two cases must now be edited in opposite directions to conceal a retune — emptying an entry
  satisfies the matrix and fails the property, deleting the hop satisfies the property and
  fails the matrix's exhaustiveness. Verified: the retune now fails BOTH.
  (b) **By-name genuinely distinguishes from at-least-one.** If the kill migrates, the computed
  value becomes `['the varied-geometry row']` and the assertion fails. Not a restatement.
  (c) **The hop list is complete for what its header claims.** Brute-forced all linear `ap + b`
  (`a ∈ [-3,3]` step 0.5, `b ∈ [-6,6]`) plus the `ceil/floor/round(p/2)`, `p % 4`,
  `max(1, p-1)`, `min(p, 2)` family for any `f` with `f(4) = 2` AND `f(6) = 5`: exactly one
  survivor, `1.5p − 4`, which nobody writes. `pageCount - 2` was deliberately NOT padded in —
  it fits the pattern but the header's criterion is "a real thing someone writes", and diluting
  that criterion is what makes such a list stop being reviewable.
  **The residual, judged NOT acceptably bounded and deferred to green rather than absorbed:**
  writing `visiblePageNumber: 3` as a raw literal, bypassing the import, leaves the fixtures
  untouched and crossRow green while `pageCount - 1` ships. That is the same defect one layer
  over, and the RED's framing understated it. It is not closable from here without a
  source-text-scanning test or a lint rule, and during RED the cases are skipped, so the
  exposure opens only at `green-frontend` — where it belongs. The partial bound is real but
  non-executable: both files derive `visiblePageNumber` from `row.currentPage`, so the bypass
  requires deleting a live import usage in a file whose header forbids it in a paragraph.
  **Also surfaced: `npm run typecheck` (`tsc -b --noEmit`) is RED at HEAD and has been.**
  `paginationState.ts(100,39): error TS6133: 'input' is declared but its value is never read`,
  exit 2 — the stub's unused parameter. Every prior step in this scenario reported "tsc clean"
  using `tsc --noEmit`, which is exit 0 and never surfaces it. The two commands disagree and
  this file recorded only the passing one. It resolves itself when green implements the stub,
  but no step should claim a clean typecheck on the strength of the weaker command again.
- [x] red-frontend (premortem CREDIBLE 1 + agent-review CONCERNS 1 and 2 over `fabafd1d`, one
  root) — **the numbers moved into the fixture; the geometry that justifies them did not.**
  `laidOutRows.fixture.ts` holds `pageCount: 4` and `pageCount: 6` and describes "seven blocks
  totalling 2800px against 900px" in the header of a file containing neither `blockHeights` nor
  `usableContentHeight`. `rowsRefuting` computes entirely off `(pageCount, currentPage)` and
  never sees the geometry. **That is the defect this very unit set out to kill — a cross-file
  binding held by a comment — reproduced one field over.** It is NOT the known raw-literal
  bypass: that is about dodging the import, this is about the imported value having no
  executable tie to its own derivation. The three chartered steps queued to edit
  `AMPLY_MEASURABLE_DOCUMENT` can now change the geometry and leave `pageCount: 4` stale, with
  crossRow green while its whole matrix reasons about a count the geometry no longer produces.
  Every case that would evaluate the claim is `.skip`ped, so the divergence is undetectable for
  the entire RED phase — and at green the natural repair to `expected 4, received 5` is to
  retune the fixture number, not the geometry.
  **Half the invariant is executable and half is still prose.** `RULED_OUT_CURRENT_PAGE_HOPS`
  covers derivations of `currentPage` from `pageCount`; the symmetric family — derivations of
  `pageCount` from the geometry — is argued at equal length in BOTH headers ("`6` is reachable
  from no other value in either file — not `4`, not the `1`/`3` skeleton counts, and not
  `blockHeights.length` (11)") and refuted nowhere executable. The fixture module cannot model
  it, because it does not import the geometry. This collision has already bitten once in this
  scenario: `railSkeletonCount: 3` colliding with `blockHeights.length === 3`. Incident: green
  ships `pageCount: blockHeights.length`, right on the fixtures and wrong on every real
  document, and the rail renders one row per block.
  Also: the fixture claims each number's rationale moved to where the number now lives — true
  for `2` and `5`, false for `4` and `6`. And `measuring.test.ts`'s header still says "Only the
  number is shared", singular, while the diff made `pageCount` a SECOND shared value
  (`pageCount: FONT_GATE_ROW.pageCount`) — and `pageCount` is not a pass-through, it is the
  derived value, the one field whose expectation had a reason to stay an independent literal.
  Guard: move the geometry into `LaidOutRow` so a collision test is writable at all, then assert
  no expected field value of a row (`pageCount`, `sheetSkeletonCount`, `railSkeletonCount`)
  equals `blockHeights.length`, a hardcoded constant, or another expected value.
  **ATTEMPTED AND INTERRUPTED — nothing of this step is committed.** The red-agent died on an
  API stall mid-run after 7 tool calls, having rewritten `laidOutRows.fixture.ts` only
  (80 → 119 lines, geometry moved into `LaidOutRow`) with no consumer rewritten, no collision
  assertion written, and no mutation verified. The partial tree was coherent by luck —
  `tsc --noEmit` exit 0 and the editor suite `2 passed | 3 skipped`, unchanged — because
  adding fields to the row type breaks no existing reader. It was **reverted**, so `HEAD`
  (`b5b6bd07`) remains the last verified state; a copy of the partial fixture is in the
  session scratchpad as `laidOutRows.fixture.partial.ts` if it is worth reading, but the work
  is small enough to redo. **To resume:** start this step from scratch, full sequence
  (red-agent → `/test-review` → behavior commit → `/refactor` + the two review passes →
  refactor commit). Nothing here has been reviewed.
  Note for the retry, from the interrupted attempt's own shape: moving the geometry into the
  row is the easy half and it is where the agent spent its budget. The load-bearing half is
  keeping `AMPLY_MEASURABLE_DOCUMENT` a single visible local binding in `measuring.test.ts`
  that BOTH font-gate cases are spread from — if the geometry now comes from the fixture, the
  two cases must still read it through one local binding, never independently, or the
  discard-the-argument kill dissolves.
  **Done on the retry.** RED as predicted: `Error: Not implemented` at
  `paginationState.ts:101:9`, `3 failed | 4 passed` (the live crossRow cases green), none
  reaching an `expect`; re-skipped. `LaidOutRow` now carries `blockHeights` and
  `usableContentHeight` beside `pageCount`/`currentPage`, so the derivation and its result are
  one value. New fixture exports: `splitAnywherePageCount(row)` (the `ceil(sum/usable)` lower
  bound — greedy agreement stays with its own chartered step), `SURFACE_CONSTANTS` (`1`/`3`/`0`,
  named ONLY to be refuted against, never as expectations), `namedValuesOf(row)`. The `4`/`6`
  rationale is now actually in the file that holds them, and says they are PRODUCED, not chosen.
  **All three mutations die**, and the headline one fires with every stub case still skipped —
  the exact state in which nothing failed before: (1) retune `FONT_GATE_ROW.usableContentHeight`
  900 → 600 leaving `pageCount: 4` stale → `1 failed | 3 passed | 3 skipped`,
  `expected {'the font-gate row': 5, …} to strictly equal {'the font-gate row': 4, …}`;
  (2) `pageCount: blockHeights.length` (4 → 7) → `3 failed | 1 passed | 3 skipped`, the
  collision test naming it `+ "pageCount === blockHeights.length"`; (3) the earlier hops still
  die on the charted division of labour — `currentPage: pageCount - 1` by the font-gate case
  only, `pageCount / 2` by the varied-geometry case only, each `1 failed | 6 passed`.
  **Co-location survived the move:** `AMPLY_MEASURABLE_DOCUMENT` is still one visible local
  binding both font-gate cases are spread from, and neither case reads `FONT_GATE_ROW` for any
  INPUT — `fontStatus` remains the only per-case difference, so the discard-the-argument kill
  stands. The second case reads the row only on the EXPECTATION side, which is the intended
  pass-through pin.
  `/test-review` answered the four judgement calls and found one real defect:
  (a) **`splitAnywherePageCount` is a real check, not a restatement** — derived side reads the
  geometry, declared side is the literal. The "edit both in one motion" escape is closed, but by
  a DIFFERENT case rather than an opposing one: retuning geometry and `pageCount` together
  satisfies this case, and is then caught by the hop matrix. Verified on the load-bearing
  instance — retune the font-gate row to 2700/900/`pageCount: 3` and `pageCount - 1` becomes
  `2` = `currentPage`, so `rowsRefuting` returns `[]` and BOTH the matrix and its non-emptiness
  companion fail. Geometry cannot be retuned into agreement silently.
  (b) **The collision check was NOT complete for what the headers claim — fixed.**
  `collisionsWithin` compared pairs inside a single row only, while `laidOut.test.ts` claims `6`
  is reachable from no other value "in either file — not `4`", and rests the whole second row on
  "the frozen literal emits `4`/`2` where this expects `6`/`5`". That CROSS-ROW distinctness —
  the entire carry of the frozen-literal kill from one row to the other — was asserted by
  nothing. Added a fifth live case plus `rowValuesOf`, proved to bite by mutation: give the
  font-gate row six blocks still summing 2800px (so `pageCount` stays `4` and every other case
  stays green) and only the new case reddens, naming
  `"the font-gate row.blockHeights.length === the varied-geometry row.pageCount"`. The surface
  constants are deliberately excluded from the cross-row half and kept in the same-row half —
  both rows name the same `1`/`3`/`0`, so including them would report every row colliding with
  every other and the check would say nothing. The pair is keyed by name, so a third row added
  without extending the expectation fails here rather than going unchecked.
  (c) **`SURFACE_CONSTANTS` framing holds.** Referenced only through `namedValuesOf` into the
  collision check; no test imports them, each file still spells `1`/`3`/`0` at its own
  assertion, and the keys are prose (`'the measuring surface's three rail rows'`) rather than
  field names, so they cannot be spread into an expectation object. Nothing asserts a constant
  against itself.
  Suite 638 passed / 6 skipped / 0 failed; `tsc --noEmit` exit 0. Files: fixture 150, crossRow
  142, measuring 193, laidOut unchanged — all under 200, and no case joined the closed measuring
  file.
- [x] red-frontend (agent-review CONCERNS 1 + premortem CREDIBLE 1 over `08404a9e`, both
  independently) — **it happened a fourth time: `SURFACE_CONSTANTS` is the geometry defect
  relocated.** This unit's whole thesis is that `pageCount: 4` sitting next to a PROSE
  description of blocks it did not contain was a cross-file binding held by a comment — and it
  then created three fresh literals with exactly that property. `1`, `3` and `0` are the values
  asserted at `measuring.test.ts:98-99,185-186` and `laidOut.test.ts:78-79` as raw literals, and
  re-typed in the fixture with only a doc comment linking them; the doc says the quiet part
  itself: "They are not the expectations — each test file still spells its own skeleton counts
  out at its own assertion." Nothing derives one set from the other, nothing compares them, and
  `Readonly<Record<string, number>>` means not even the compiler links them.
  Incident, and it is the exact family the fixture's own docstring calls "not hypothetical: it
  shipped in this scenario once": the rail grows to four rows (a design change, or `align-design`
  matching the mockup), so `measuring.test.ts:99` becomes `railSkeletonCount: 4` while
  `SURFACE_CONSTANTS` still says `3`. `FONT_GATE_ROW.pageCount` is `4`, so
  `railSkeletonCount: pageCount` is now a live collision — satisfying the fixture and wrong on
  every real document. `collisionsWithin` reads the stale `3` and reports `[]`, and the collision
  case passes while asserting BY NAME that no such echo exists. Same with a row retuned to four
  blocks and `railSkeletonCount: blockHeights.length`. The guard against a stale constant is
  review, not a test — the failure mode the last three units were each written to end.
  `/test-review`'s finding (c) checked only the opposite direction (that the constants cannot be
  spread INTO an expectation object); drift AWAY from the assertions was never considered.
  Guard: the same mechanical fix the geometry got — the test files read their skeleton counts
  from the fixture at the assertion, or a live case compares the constants against the values
  those files expect. Latent today (the values do agree), but every chartered step queued
  against these surfaces can move a skeleton count, with the cases that would notice `.skip`ped
  for the whole RED phase — verbatim the condition that let the last one survive.
  **Done, and the two goals turned out not to conflict.** The twice-adjudicated NO ACTION was
  against SPREADING a constants object into an expectation — right, because a spread deletes the
  key list from the assertion. A PER-FIELD named reference does not: every key stays typed out,
  and only the VALUE comes from one declaration. New in the fixture:
  `MEASURING_SURFACE = { sheetSkeletons: 1, railSkeletons: 3 } as const` and `NO_SKELETONS = 0`,
  with `SURFACE_CONSTANTS` keeping its prose keys but now BUILT FROM those bindings — so the
  values `collisionsWithin` refutes against and the values the cases expect are one declaration.
  **The anti-spread property is structural, not conventional:** the object's keys are
  deliberately NOT the field names (`sheetSkeletons` ≠ `sheetSkeletonCount`) and the zero is a
  separate scalar rather than a third member, so a spread injects two wrong keys and omits two
  required ones and `toStrictEqual` fails on four counts. `/test-review` confirmed by trying it,
  and found `NO_SKELETONS` is not the weaker link the question suspected — spreading a number
  yields no keys at all, so it fails harder than the object would. Side benefit: the non-matching
  key names let both imports sit on one line, so `measuring.test.ts` grew by 1 line, not 5, and
  no split was needed.
  RED as predicted: `Error: Not implemented` at `paginationState.ts:101:9`, `3 failed | 5 passed`,
  none reaching an `expect`. One correction loop: the first prediction said `4 passed` —
  `crossRow` has five live cases, not four — corrected and re-run before verifying.
  **Mutation 1 is the whole point, and it was checked in both directions:** the incident (rail
  grows to four rows, `railSkeletonCount: 4`) now **kills** — `1 failed | 4 passed | 3 skipped`,
  firing with all three stub cases still skipped — while **the identical edit at HEAD survives**
  (`5 passed | 3 skipped`, zero failures), confirming "today it fails nothing" rather than
  assuming it. `/test-review` mutated the new bindings directly too: `NO_SKELETONS = 2` →
  `"the laid-out phase's zero skeletons === currentPage"`; `railSkeletons = 4` →
  `"the measuring surface's three rail rows === pageCount"`. All four earlier kills still land on
  their charted division of labour (stale geometry; `pageCount: blockHeights.length`;
  `currentPage: pageCount - 1` by the font-gate case only; `pageCount / 2` by the varied one).
  `/test-review` found one real defect — **the positively-absent pin had been weakened.**
  `laidOut.test.ts` had rewritten its load-bearing sentence from "exact `0`/`0`/`null`/`false`/`''`"
  to "(`NO_SKELETONS` twice, then `null`/`false`/`''`)", deleting the zero from the only place a
  reader could see it. The pin's whole point is that `0` for a phase rendering no skeletons is
  DECIDED here, not inherited from an interface or from a binding's name. Literal zeros restored,
  with the reason the binding is read anyway stated alongside; header only, no assertion or
  expected value touched. `measuring.test.ts` still spells its own out, so it needed no
  equivalent.
  Suite 638 passed / 6 skipped / 0 failed; `tsc --noEmit` exit 0. Files: fixture 175, measuring
  194, laidOut 90, crossRow 142 untouched — all under 200, no case joined the closed measuring
  file.
  **Carried forward, currently only in a doc comment:** `MEASURING_SURFACE` is now the ONLY place
  a design change to those surfaces can be made, so the collision test will redden on any
  legitimate rail-count change. The correct repair at that point is to retune the row geometry so
  `pageCount ≠ 4` — NOT to loosen the check. Whoever hits that redness needs to know it is the
  guard working, not a false positive.
  **That "will redden on any change" claim is FALSE, and both review passes proved it
  independently — see the three steps below.** `collisionsWithin` is a uniqueness check, so it
  reddens only when the new value equals another number of the same row; `railSkeletons: 8`
  changes four assertions in silence. Do not rely on this sentence.
  One residue, deliberately left: nothing forces a NEWLY ADDED surface constant to be routed
  through `SURFACE_CONSTANTS`. That is the name-keyed map exhaustiveness item below.
- [x] red-frontend (agent-review CONCERNS 1 + premortem CREDIBLE 1 over `5eec272c`, both
  independently) — **the fifth time, and this one is worse than its predecessors: the mutation
  kill was an accident of two row numbers, and the copy that used to backstop it is gone.**
  `collisionsWithin` is a UNIQUENESS check, not a VALUE check. It fires only when the mutated
  constant equals another number of the same row, and the live value sets are
  `{1,3,0} ∪ {4,2,7}` and `{1,3,0} ∪ {6,5,11}`. The two kills the last unit reported —
  `railSkeletons = 4`, `NO_SKELETONS = 2` — landed exactly on `pageCount` and `currentPage`.
  **That is the only reason they killed.** Set `railSkeletons: 8` or `9`, or `sheetSkeletons:
  1 → 9 / 12 / 100`, or `NO_SKELETONS: 9`: no collision in either row, constants are excluded
  from `collisionsAcross` by design, the suite stays 638/0 — and the expected value has been
  silently rewritten in two files and four assertions at once, in cases `.skip`ped for the whole
  RED phase. Two data points inside the kill set were read as a property of the whole set.
  Before this unit a fixture edit could not move an assertion, because the assertion held its own
  literal; after it, one token does. **The unit closed the DRIFT hole and opened a
  SILENT-REDEFINITION hole, with a bigger blast radius and a guard that was never designed for
  this role** — the collision check was conscripted into being the constants' guard without
  anyone checking its coverage. Grep confirms nothing in `frontend/src` or `acceptance/` pins
  `sheetSkeletons === 1`, `railSkeletons === 3`, `NO_SKELETONS === 0` (the acceptance-layer
  `MEASURING_SURFACE` is an unrelated locator tuple). Guard, and it must be LIVE since
  `crossRow.test.ts` is the only file that runs during RED:
  `expect({ ...MEASURING_SURFACE, zero: NO_SKELETONS }).toStrictEqual({ sheetSkeletons: 1,
  railSkeletons: 3, zero: 0 })`, with a header stating this is the one place the design numbers
  are decided and a legitimate rail-count change is edited HERE, deliberately.
  **Done.** New file `paginationState.designNumbers.test.ts` (68 lines), **LIVE not skipped** — it
  checks the constants, not the stub, so it runs today. Own file rather than joining
  `crossRow.test.ts`: these constants are precisely what `crossRow` EXCLUDES from its cross-row
  half, and `crossRow` at 142 lines must keep headroom for the chartered companion case. The
  recorded shape was taken rather than a mockup scrape — scraping would pin the number to CSS
  classes in a non-normative artifact with no testids, reddening on a cosmetic mockup edit and
  staying green on a rail redesign that keeps three divs for another purpose; and a scrape is not
  a DECISION SITE, which is what this step's charter asks for. Mockup and spec provenance is in
  the header instead.
  **The hole proved rather than assumed:** `railSkeletons: 3 → 8` **SURVIVES at HEAD** —
  `5 passed | 3 skipped`, ZERO failures — and is killed by the new case (`- 3 / + 8`). Also
  killed: `sheetSkeletons: 1 → 9`, and `NO_SKELETONS: 0 → 9` (the latter fails on ONE case only,
  `collisionsWithin` silent, confirming the thesis directly). Every previously-recorded kill still
  lands, and `railSkeletons = 4` / `NO_SKELETONS = 2` now fail TWICE — the collision check plus the
  new value check.
  RED as predicted: unskipping the three stub cases gives `3 failed | 6 passed`, all
  `Error: Not implemented` at `paginationState.ts:101:9`, none reaching an `expect`; the new case
  passes unmutated. No correction loop.
  **Is this the "value typed twice with nothing comparing them" pattern one level over? Answered
  honestly, and `/test-review` verified the load-bearing half by mutation rather than taking it.**
  It is genuinely different: in all five prior repetitions the two copies were compared by nothing
  executable — a doc comment, a `.skip`ped case, or a uniqueness check that never read the value.
  Here the comparison runs on every suite run during RED, turning a one-token silent rewrite into a
  red test. But it is a **TRIPWIRE, not a DERIVATION**: both sides are authored in this repo, so a
  wrong-but-deliberate change is a two-file edit rather than an impossible one. That limit is
  stated in the file's own header under `WHAT IT DOES NOT CLAIM`, so no later reader inherits the
  last unit's mistake of over-claiming a guard's coverage — and `/test-review` checked for exactly
  that repeat and found none.
  `/test-review` ran five fixture mutations against both live files: `railSkeletons: 8`,
  `sheetSkeletons: 9`, `NO_SKELETONS: 9`, adding a fourth member, and removing one — **all five
  RED in designNumbers and GREEN in crossRow.** That green column is the independent confirmation
  that `collisionsWithin` never guarded these values. The add/remove pair also proves the spread
  is safe here: `toStrictEqual` over `{ ...MEASURING_SURFACE, zero: NO_SKELETONS }` makes the check
  exhaustive over the object's members, and the mistaken-licence risk is mechanical rather than
  prose — the fixture's keys are deliberately not the field names, so spreading it into a
  `PaginationViewState` expectation fails on the key list.
  One fix applied: four of the header's five cross-references pointed at the wrong lines
  (`measuring.test.ts:98-99` → 99-100, `:185-186` → 186-187, `laidOut.test.ts:78-79` → 82-83,
  `02-measuring.html:52` → 53). A header whose whole function is to point at the assertions it
  guards, misdirecting the reader, is the same class of defect as prose over-claiming coverage.
  **New finding, flagged not absorbed — there is a THIRD copy of the `3`, in Python.**
  `acceptance/statements/frontend/editor/pagination_measuring_locators.py:77` holds
  `EXPECTED_RAIL_SKELETON_COUNT = 3`, with its own justification comment, compared with the
  TypeScript one by nothing. (The `MEASURING_SURFACE` locator tuple in that file is unrelated —
  this is a separate constant.) Cross-language, acceptance-layer; no vitest case can close it and
  none should try. Its own step, below.
  Suite 639 passed / 6 skipped / 0 failed; `tsc --noEmit` exit 0.
- [x] red-frontend (agent-review CONCERNS 1 over `36574438`) — **the sixth instance, and the
  header does not admit this one.** `designNumbers.test.ts:9-10` claims the four assertions and the
  collision check "share ONE declaration… deliberate and not being undone here" — a claim about
  four lines in two OTHER files, checked by nothing. The new case pins the FIXTURE'S values; it
  does not pin that `measuring.test.ts:99-100,186-187` and `laidOut.test.ts:82-83` still read
  `MEASURING_SURFACE.railSkeletons` / `NO_SKELETONS` rather than re-typed literals. Edit
  `measuring.test.ts:100` to `railSkeletonCount: 3` and: `designNumbers` green (fixture untouched),
  `collisionsWithin` green (it reads `SURFACE_CONSTANTS`, not the assertion), and the drift hole the
  sharing exists to close is reopened in one token — inside a `.skip`ped case, so undetectable
  until green. Worse than its predecessors because this unit's `WHAT IT DOES NOT CLAIM` block
  ENUMERATES limits (not-right, the Python copy, the mockup) and omits this one, so a reader taking
  that block as complete inherits exactly the over-claim the unit was written to correct. Guard:
  assert the assertion SITES reference the constants — a source-text check over the two files, or
  unskipped cases driven from the fixture. No vitest case in the diff can do it.
  **Done.** New file `paginationState.constantSites.test.ts` (165 lines, **LIVE**), a SOURCE-TEXT
  check, because the claim is about how an expectation is WRITTEN: `railSkeletonCount: 3` and
  `railSkeletonCount: MEASURING_SURFACE.railSkeletons` evaluate identically, so no runtime
  assertion over values can separate them. It ingests both files via Vite `?raw`, strips comments
  (`measuring.test.ts:120-121` discusses these fields in prose), collects every
  `sheet|railSkeletonCount:` assignment **in order with its right-hand side**, and compares the two
  lists in one `toStrictEqual`. That form catches a re-typed literal, an added or deleted
  assertion, a renamed constant, and a swapped field→constant pairing.
  **Hole proved, not asserted.** The chartered mutant `measuring.test.ts:100 → railSkeletonCount:
  3` **survives at HEAD** (`6 passed | 3 skipped`, zero failures — `designNumbers` green because
  the fixture is untouched, `collisionsWithin` green because it refutes against
  `SURFACE_CONSTANTS`) and is killed by the guard. Same for transposing `:99-100` and for
  `laidOut.test.ts:82 → sheetSkeletonCount: 0`.
  **One correction loop in RED:** predicted a plain pass, got `TypeError: The URL must be of scheme
  file` — under jsdom `import.meta.url` is not a `file:` URL, so `fileURLToPath` throws. Test-setup
  mechanics, not the subject.
  **`/test-review` found the hole this step's own charter did not name, one level up.** Replace the
  import with a local redeclaration — `const MEASURING_SURFACE = { sheetSkeletons: 1,
  railSkeletons: 3 }` — and all six assertion lines stay BYTE-IDENTICAL: guard green, `designNumbers`
  green, `collisionsWithin` green, sharing severed. An assignment list reads a NAME; a name is worth
  only where it is bound. Fixed by collecting each file's fixture import specifier list as a list
  and comparing it in the same `toStrictEqual`, so deleting the import fails as loudly as editing a
  site. Keeping the import AND shadowing it locally is not a third route — that is a TS
  redeclaration error. Eight mutations killed after the fix.
  **Fail-closed against formatting**, verified over six variants (line wrap, doubled space,
  `MEASURING_SURFACE['railSkeletons']` bracket form, `3` behind a same-line comment, `3` across a
  wrap, trailing space): anything not exactly `<field>: <expression>,` on one trimmed line is
  DROPPED rather than admitted, so the list shortens and the check fails. Two consequences now in
  the header: a re-typed literal surfaces as a MISSING member, not a changed one; and the
  strictness is load-bearing — widening the regex to tolerate wrapping is what makes the
  trailing-comment attack start passing. `prettier --check` is clean on both files (widest site 59
  columns against `printWidth: 100`), so `npm run format` cannot redden it.
  **Second `/test-review` defect: the new file did not typecheck.** `node:fs`/`node:path`/`process`
  are untyped — `tsconfig.app.json` covers `src` with `"types": ["vite/client"]`. It ran green
  under vitest only because esbuild strips types. Adding `"node"` was refused (it would make
  `process.env` legal in frontend source); ingestion moved to `?raw`, which also fails at transform
  time on a wrong path and drops the assumption that vitest always runs from `frontend/`.
  Header over-claim fixed in `designNumbers.test.ts` (67 → 80 lines, header only): "four
  assertions" → six, it no longer implies it guards the sharing, and `WHAT IT DOES NOT CLAIM` gains
  both the omitted limit and the sentence that the block lists KNOWN limits and is not a proof no
  others exist — which is what let a reader inherit the over-claim.
  Suite 640 passed / 6 skipped / 0 failed; `tsc -b --noEmit` and oxlint clean except the
  pre-existing RED stub `paginationState.ts:100` (unused `input`). Files: constantSites 165,
  designNumbers 80 — under 200.
- [ ] red-frontend (premortem CREDIBLE 1 over `c0e35fc6`) — **the guarded defect class ships one
  field over, and the header's reason for excluding it is false in the same way the last header
  was.** `SKELETON_ASSIGNMENT` is scoped to `sheet|railSkeletonCount`, but `measuring.test.ts:184-185`
  and `laidOut.test.ts:80-81` are the SAME construct — a fixture constant read by name at an
  assertion site. The header says `pageCount`/`currentPage` are "guarded from the value side by
  `crossRow.test.ts`'s derivation check". They are not: `crossRow.test.ts:126` derives from
  `row.blockHeights` and compares against `row.pageCount` — **the fixture's declared field, never
  the test file's assertion**. Retype `pageCount: 4` at `:184` and `crossRow` is untouched (fixture
  unchanged), `designNumbers` is untouched (it pins only the surface constants), `constantSites` is
  untouched (wrong field name), and all six skeleton lines stay byte-identical. That is the
  chartered mutant re-run one line up, surviving. Incident: the reader on sheet 3 of a 6-page
  document sees "Страница 5 из 4". Guard is one alternation away:
  `/^(pageCount|currentPage|(?:sheet|rail)SkeletonCount): (.+),$/`, with `pageCount: null` /
  `currentPage: null` as legitimate members of the expected list.
- [ ] red-frontend (premortem CREDIBLE 2 over `c0e35fc6`) — **nothing forces the three `.skip`s off
  at green, and this unit walked past the one file that could see them.** `constantSites` already
  ingests both files AS TEXT and reads their assertion lines, and never looks at `it.skip`. The
  pinned assignment list is IDENTICAL whether the cases are skipped or not, so the file certifies a
  healthy assertion surface for cases that do not run — the invisible-until-green hole, left open at
  the one moment it matters. (Sharpens the `36574438` skip-exit step below, which asked for a
  live case reading the three files' sources: `constantSites` is now that reader.) Guard: pin the
  `it.skip(` count in those two files as an EXPECTED value — 3 today, 0 at green — so green cannot
  be declared without the expectation being edited in the same commit.
- [ ] red-frontend (premortem CREDIBLE 3 over `c0e35fc6`) — **prettier CAN redden this file, through
  the import line the verification never measured.** The header's immunity claim is scoped to the
  assignments (widest 59 of 100). `FIXTURE_IMPORT` is equally single-line and equally fail-closed,
  and `measuring.test.ts:3` is **86 columns** — 14 of headroom. Any added specifier ≥15 chars
  (`SURFACE_CONSTANTS` is 17) makes prettier wrap it, and the failure then reports
  `fixtureImports: []`, literally "the import was deleted", against a file where it is plainly
  present. Under a red suite mid-green the on-call repair is the one the header forbids — loosen
  `FIXTURE_IMPORT` — which re-opens the local-redeclaration hole `/test-review` just closed. Guard:
  a probe case pinning the multi-line import shape, or at minimum the measured 86/100 budget stated
  in the header so the next author knows one specifier is the whole margin.
- [ ] red-frontend (agent-review CONCERNS 1 over `c0e35fc6`) — **the header's stated defense against
  local shadowing is factually wrong, and the real defense is incidental and undocumented.** The
  header says keeping the import and shadowing it locally "is a TypeScript redeclaration error and
  dies at `tsc --noEmit`". True only at MODULE scope. A block-scoped shadow inside a `describe` or
  `it` callback is legal TS — run, not argued: minimal repro under this repo's own tsc with
  `--strict --noUnusedLocals` exits 0, with the assertion site byte-identical. What actually blocks
  the attack today is `"noUnusedLocals": true` plus the accident that every constant is read from
  exactly ONE scope (`MEASURING_SURFACE` at `:99-100`, `NO_SKELETONS` at `:186-187` and
  `laidOut:82-83`), so shadowing orphans the import. The moment any constant is read from two
  `describe`s — which green and the queued surface steps make likely — the shadow is invisible to
  tsc, to this guard, and to `designNumbers`. The condition it rests on is stated nowhere.
- [ ] red-frontend (agent-review CONCERNS 3 over `c0e35fc6`) — **the seventh-assertion-in-a-third-file
  hole is held open by a two-element hardcoded list, when a glob was available.** `SOURCES` names
  exactly `measuring` and `laidOut`; the header disclaims a third file as "outside its window
  entirely", which restates the limitation rather than giving a reason for it. The file's own
  strongest argument — a check that merely greps passes while a seventh assertion is added with a
  raw literal — applies verbatim to a new FILE. `import.meta.glob('./paginationState.*.test.ts',
  { query: '?raw', eager: true })` works in this exact toolchain, removes the hardcoded list, and
  makes a case MOVED between files fail for the right reason. As shipped, adding
  `paginationState.someNewCase.test.ts` with `railSkeletonCount: 3` is green everywhere — and three
  chartered steps are queued against these surfaces.
- [ ] docs (agent-review CONCERNS 2 over `c0e35fc6`; fold into the next edit of the file) — **"npm
  run format cannot redden this case" is a manual measurement of a moving target, pinned in a
  comment.** True today (59 of 100). A longer constant name, a nested field, or a `printWidth`
  change wraps a line, the list SHORTENS, and the case reddens with a message reading "an assertion
  is missing" rather than "the formatter reflowed line 100" — while the header simultaneously
  forbids the reader from loosening the regex, leaving the recovery path documented only in prose.
- [ ] red-frontend (premortem CREDIBLE 1 over `36574438`) — **even when the sites DO read the
  constants, nothing pins WHICH FIELD each reaches.** Distinct from the finding above, and a guard
  for that one which merely asserts the constants are referenced does NOT close this. The fixture
  deliberately makes its keys not the field names (`sheetSkeletons` ≠ `sheetSkeletonCount`) so a
  spread cannot be the shorter thing to write — sound for its purpose, and precisely what removes
  the last mechanical link between a constant and the field it feeds. Transpose the two reads at
  `measuring.test.ts:99-100` (`sheetSkeletonCount: MEASURING_SURFACE.railSkeletons` and vice versa):
  the fixture is untouched, so `designNumbers` passes, `collisionsWithin` passes (`namedValuesOf`
  still yields `{1,3,0,…}`), and the matrix, the collision halves and the derivation check never
  look at that file. At green the implementation is written to match the transposed expectation and
  the whole vitest suite is green with the surface INVERTED — 3 skeleton sheets, 1 rail row. The
  only thing that would redden is the Selenium leg's `EXPECTED_RAIL_SKELETON_COUNT`, the copy this
  same unit flagged as bound to TypeScript by nothing. Guard: a live case pinning the measuring
  surface's expected `(sheetSkeletonCount, railSkeletonCount)` pair as an object built from the
  constants, so the two cannot swap without an expectation moving. The values are asymmetric
  (`1` vs `3`), so the transposition is detectable — nothing detects it.
- [x] test-review follow-up to the step above — landed as `c2d76b3d`, and it closed a defect the
  `designNumbers` unit did not create but sat next to. `crossRow.test.ts:127` read BOTH sides of
  the hop-count equality out of the same fixture module
  (`byName(splitAnywherePageCount)` vs `byName((row) => row.pageCount)`), so a retune that moves
  `blockHeights` and `pageCount` TOGETHER keeps the two sides equal and leaves `4` and `6` pinned
  by nothing. The literal is now a third side:
  `{ derived: byName(splitAnywherePageCount), declared: byName((row) => row.pageCount) }` against
  `{ derived: counts, declared: counts }`. Not accepted on argument — the first distinguishing
  mutant was invalid (font-gate `pageCount: 8` also moved the hop matrix, so it died at HEAD too);
  the valid one is `usableContentHeight 900→350`, `pageCount 4→8`, `currentPage 2→4`, which
  preserves the hop matrix and both collision checks: **survives at HEAD (5 passed), killed after
  the fix (1 failed / 4 passed)**. `/test-review` also declined to move `collisionsWithin` and
  friends into the fixture — it would break the 200-line cap AND put the checker in the module it
  checks, the exact defect this scenario has spent the week closing. `/refactor`: NO ACTION from
  all three detectors. Suite 639 passed / 6 skipped / 0 failed; `tsc --noEmit` exit 0; oxlint
  clean. crossRow 153 lines. **Note the greedy-agreement step chartered against `fabafd1d` below
  is now MORE urgent, not less:** the added literal `4` makes the count LOOK pinned, while a
  `usableContentHeight 900→700` retune keeps `ceil(2800/700) === 4` and all three live cases
  green — and packing-agnosticism (`400+380 | 420+390 | 410+400 | 400`) is FALSE at 700px, where
  greedy no-split gives 7. The literal that reads as protection covers neither half of that claim.
- [ ] red-frontend (agent-review CONCERNS 1 + premortem REMOTE 1 over `c2d76b3d`, same finding;
  cheap) — **the exhaustiveness claim is defeated by exactly one member name.**
  `expect({ ...MEASURING_SURFACE, zero: NO_SKELETONS })` puts `zero` AFTER the spread, so a fourth
  member literally named `zero` is silently overwritten and its addition PASSES — while the header
  claims without qualification that "adding a fourth member to `MEASURING_SURFACE` … fails here".
  `/test-review`'s fourth-member mutation used some other name, so it never probed the one name
  that survives. Narrow, but `MEASURING_SURFACE`'s keys are deliberately NOT the field names, so a
  short abstract key is exactly the register a future member is drawn from. Fix: order `zero`
  before the spread so a real collision fails, or give the scalar a key that cannot collide — plus
  the qualification in `WHAT IT DOES NOT CLAIM`.
- [ ] docs, or fold into the next edit of the file (agent-review CONCERNS 3 over `c2d76b3d`;
  trivial) — **the header says "the three stub-driven files"; there are TWO.**
  `measuring.test.ts` and `laidOut.test.ts` hold THREE skipped CASES between them. A header whose
  job is to tell a future reader which files run today, miscounting the files, is the same class
  as the four line-number references `/test-review` corrected one unit earlier.
- [ ] red-frontend (premortem CREDIBLE 2 over `36574438`) — **nothing forces the three skipped
  cases to unskip at green, and the counter that was supposed to catch it cannot.** The whole
  architecture of this unit and its four predecessors rests on "the stub cases are skipped for all
  of RED, so the guard must be live" — an arrangement whose EXIT condition is enforced by nothing
  executable. All five guards are fixture-internal; none calls `derivePaginationState`. Unskip two
  of three and miss `laidOut.test.ts`, and the varied-geometry row — the SOLE killer of both the
  frozen-literal mutation and `currentPage: pageCount / 2` — asserts nothing, with the suite green.
  The precedent is in the repo: `grep it.skip frontend/src` returns six, three from this scenario
  and three in `ManualEditor.autosaveAbandon*.test.tsx` last touched `2c07d89d` on 2026-08-02, a
  different story still parked. So the whole-suite skip counter conflates two stories, and a green
  run that unskips two of three reads `5 skipped` — the number the log already recorded three units
  ago. (This sharpens the scoped-zero deliverable already charted at the green step: scope it to
  these three files by name, not to a directory or a count.) Guard: a live case reading the three
  files' sources and asserting zero `it.skip` among them.
- [ ] red-frontend (premortem CREDIBLE 3 over `36574438`, low severity) — **the mockup binding got
  no step while the Python one did.** The header calls the file "THE ONE PLACE THE MEASURING
  SURFACE'S DESIGN NUMBERS ARE DECIDED" and, twenty lines later, "the mockup is the actual source
  (`02-measuring.html:46-48` is three rail `.skeleton` divs)". Both cannot be true: if the mockup is
  the source, this file is a second copy compared to it by prose. Rejecting the scrape was right —
  it reddens on cosmetic CSS edits and stays green on a redesign that keeps three divs — but the
  rejection produced no recorded step, whereas the structurally identical cross-language gap got
  flagged AND a `[ ]` line. The asymmetry is the finding, and the "one place decided" framing is
  what will stop the next reader from checking the mockup at all. Incident: rail redesigned to four
  rows two sprints ago, editor still renders three, suite green throughout. Guard: a step for the
  mockup↔fixture binding, and a line in `WHAT IT DOES NOT CLAIM` saying a mockup redesign is
  detected by nothing.
- [ ] red-frontend (agent-review CONCERNS 2 over `36574438`) — **the header's six line-number
  cross-references are prose that already rotted once.** All six are correct at HEAD; four of five
  were WRONG one commit ago and were repaired by `/test-review`. The repair restored accuracy
  without adding anything that keeps it, and every chartered step queued against `measuring.test.ts`
  shifts those lines. The commit message names the defect class exactly — "a header whose job is to
  locate the assertions it guards is defective when it misdirects" — and then ships the same header
  unmechanised, with no mention in `WHAT IT DOES NOT CLAIM`. Guard: anchor on a searchable token
  instead of a line number; at minimum note in the header that the references are unpinned.
- [ ] red-selenium or red-frontend (found by the `designNumbers` step) — **a third copy of the
  rail count lives in Python and nothing compares it to the TypeScript one.**
  `pagination_measuring_locators.py:77` holds `EXPECTED_RAIL_SKELETON_COUNT = 3` while
  `MEASURING_SURFACE.railSkeletons` holds `3` in the fixture. Binding them is cross-language, so
  the vitest guard cannot reach it; the natural home is the Selenium leg asserting the rendered
  rail against a value derived from one side. Until then, a rail redesign updates one language and
  leaves the other asserting the old count.
- [ ] red-frontend (premortem CREDIBLE 2 over `5eec272c`) — **the collision expectation can be
  widened on its own; its sibling cannot, and the file argues against itself about exactly this.**
  The hop matrix has a second COMPUTED case precisely so it "cannot be quietly shortened" — the
  two must be edited in opposite directions to hide a retune. The collision check got no such
  companion: its expectation is a bare literal `{ 'the font-gate row': [], 'the varied-geometry
  row': [] }`, and turning red into green is one paste of
  `['the measuring surface's three rail rows === pageCount']` — a single mechanical
  self-sufficient edit nothing refutes. Worse, the guidance against that edit ("retune the row
  geometry, not the check") lives in a doc comment on `MEASURING_SURFACE` in
  `laidOutRows.fixture.ts` — a DIFFERENT FILE from the one that reddens. The developer's red is in
  `crossRow.test.ts`, whose header never says the collision expectation must stay empty. That is
  this scenario's own defect again: a cross-file binding held by prose. Incident: rail grows to
  four rows per design, the test reddens, the fix lands as one pasted line, and three sprints
  later `railSkeletonCount: pageCount` ships — the exact hop the file asserts by name is
  impossible. Guard: a property-form companion,
  `expect(LAID_OUT_ROWS.filter((row) => collisionsWithin(row).length > 0).map((r) => r.name))
  .toStrictEqual([])`, plus the retune-the-geometry sentence in `crossRow.test.ts`'s OWN header.
- [ ] red-frontend (premortem CREDIBLE 3 + agent-review CONCERNS 2 over `5eec272c`) — **the key
  text still spells the number in words, and the number left; and one header sentence is simply
  false.** `SURFACE_CONSTANTS` keeps prose keys whose values are now imported:
  `'the measuring surface's three rail rows': MEASURING_SURFACE.railSkeletons`. Change
  `railSkeletons` to `4` and the key still reads **three** — so every collision string, every
  failure diff, every `toStrictEqual` output names a value the constant no longer holds. The last
  commit contains the artifact: its recorded kill for `railSkeletons = 4` is
  `"the measuring surface's three rail rows === pageCount"`, a label lying by one, logged as a
  passing verification. This is also what makes the finding above undetectable by review — the
  message reads correct at every value. Incident: a reviewer reads "three", checks the rail is
  three rows, concludes the collision report is stale, and deletes the entry.
  Separately, `laidOut.test.ts:64-65` states a mechanism that does not hold: "Change
  `NO_SKELETONS` to anything else and the laid-out zero collides with the measuring surface's `1`
  … which is LIVE today." Both halves are wrong — `NO_SKELETONS = 8` collides with nothing and
  the suite stays green, and the named partner is the `1` only for the single mutation
  `NO_SKELETONS = 1`; the mutation actually run (`= 2`) killed via `currentPage`, which the
  progress note records verbatim without noticing it contradicts the sentence it was validating.
  Also flagged: restoring the literal `0/0/null/false/''` to the `laidOut` header and the parallel
  "`MEASURING_SURFACE`'s 1 and 3" now in the `measuring` header re-create a prose-held literal
  describing a value that lives elsewhere. That may still be the right call for readability, but
  it should be recognised as re-opening the pattern rather than closing it. (The `7` and `4` in
  that header are fine — they ARE guarded, by `blockHeights.length` and `pageCount`.) Guard:
  derive the names (`` `the measuring surface's ${MEASURING_SURFACE.railSkeletons} rail rows` ``),
  or assert the spelled numeral in each key matches its value; and correct the false sentence.
- [ ] red-frontend or red-selenium (premortem CREDIBLE 2 over `08404a9e`) — **`usableContentHeight`
  has no producer, and this unit made the pure suite more self-sufficient about exactly the half
  that has none.** `blockHeights` and `usableContentHeight` appear in five files, all
  `paginationState.ts` and its tests; nothing in `frontend/src` measures a block or computes a
  sheet's usable height. Every packing-agnosticism argument in this scenario rests on one
  sentence — "`usableContentHeight` is already the post-margin figure, so no such packer can be
  written against this contract" — asserted nowhere. Incident: green ships, every vitest case
  green, the caller passes the sheet's BORDER-BOX height (or forgets the `@page` margin), and
  every real document reads `Страница 1 из 3` where it should read `из 4`. The fixture's `900`
  and `600` are invented and differ per row, so they cannot detect it. This is a DIFFERENT
  producer from the charted scroll one: that step owns `visiblePageNumber`, and nothing owns
  `blockHeights` / `usableContentHeight`. Guard: a Selenium assertion binding the value the
  editor passes for `usableContentHeight` to the rendered sheet's content box, with an owner.
- [ ] red-frontend (premortem CREDIBLE 3 over `08404a9e`) — **no row-well-formedness check, and
  the varied row sits exactly on the cliff edge.** `splitAnywherePageCount` is `ceil(sum/usable)`
  and notices nothing about individual blocks; `VARIED_GEOMETRY_ROW` holds two blocks of exactly
  `600` against `usableContentHeight: 600`. Three chartered steps will retune this geometry.
  Nudge usable to `590`, or a block to `610`, adjust `pageCount` to the new `ceil`, and every
  case stays green — but the document is now unpackable by ANY no-split packer, since a block
  exceeds a sheet. 2.1's greedy-agreement step then inherits a fixture whose assertion is
  unsatisfiable and reddens for a reason unrelated to the packer under test. Distinct from that
  chartered step: it pins two packers against each other GIVEN well-formed input; this pins the
  input. Guard: assert `Math.max(...row.blockHeights) <= row.usableContentHeight` for every row,
  and `usableContentHeight > 0`, which the division also assumes. (Subsumes the REMOTE that
  `blockHeights: []` with `pageCount: 0` satisfies the derivation, surviving today only because
  `collisionsWithin` incidentally catches the `0` against the zero-skeleton constant.)
- [ ] red-frontend (agent-review CONCERNS 2 + premortem REMOTE 1 over `08404a9e`, both minor;
  fold into whichever step next touches these files) — two scope defects in the new checks.
  **(a)** `rowValuesOf` includes `blockHeights.length` in the CROSS-row set, and one of the three
  pairings it produces guards nothing: font-gate `blockHeights.length` against varied-geometry
  `blockHeights.length`. No implementation returns the OTHER row's block count. A future retune
  leaving both rows with the same number of blocks reddens the test naming a "collision" that is
  not one, satisfiable only by perturbing a block count for no behavioural reason. Narrow the
  scope. **(b)** `byName`/`byRowPair` key by `row.name`, so duplicate names silently collapse a
  row out of the derivation check — and the assertion is fully symmetric, so a vanished row takes
  its own assertion with it. Today it is caught only incidentally by the sibling cases that
  hardcode the name literals; the charted exhaustiveness step will likely replace those with
  derived maps, and at that moment the whole `describe` becomes self-satisfying. Whoever takes
  that step must add `expect(Object.keys(byName(...)).length).toBe(LAID_OUT_ROWS.length)`.
- [ ] red-frontend (premortem CREDIBLE 2 over `fabafd1d`) — **scenario 2.1's open choice can be
  decided by a fixture retune nobody reads as making it.** Packing-agnosticism is the stated
  licence for pinning `pageCount` at all: the blocks pack exactly, so greedy no-split and
  `ceil(3600/600)` both answer 6. That is a fragile arithmetic coincidence of eleven literals,
  restated by hand. Any chartered edit that keeps the sum and the count but breaks exact packing
  silently makes the two candidate packers disagree, and the pinned `6` then SELECTS one of
  them — committing greedy-no-split in a red-phase 1.1 fixture, before 2.1 opens. crossRow stays
  green throughout: the pair `(6, 5)` never changed. Guard: assert that the two candidate
  packings agree on each row's `pageCount`. It is the one claim in the commit whose falsification
  is invisible in both test files AND in the new live test.
- [ ] red-frontend (premortem CREDIBLE 3 over `fabafd1d`) — **the registry is opt-in, and the
  design actively discourages registering.** `crossRow` iterates `LAID_OUT_ROWS`, a
  hand-maintained array, and nothing asserts it is exhaustive over the module's exported
  `LaidOutRow`s — a new `export const THIRD_ROW` participates in no matrix. Worse, appending a
  third row CORRECTLY turns a green `toStrictEqual` red and forces the author to re-derive four
  name-arrays for a change unrelated to their row, so the path of least resistance is to leave it
  out; the name arrays are positionally coupled too, so even a harmless reorder is a spurious
  red. Incident: a later step (2.1's packing row, or the `'failed'` arm) adds a third row in a
  third file, its numbers agree with `pageCount - 1`, its own header says the pair guards it, and
  the hop this whole unit exists to kill is live again — with nothing red. Guard: assert every
  exported `LaidOutRow` is a member of `LAID_OUT_ROWS` (`import * as rows`, check each
  `LaidOutRow`-shaped export is registered), and reconsider the positional coupling so
  registering a row is cheap.
- [ ] red-frontend (agent-review CONCERNS 2 over `2572b8be`) — **the two filenames name PHASES
  while both headers insist the seam is by SUBJECT.** `paginationState.measuring.test.ts` holds
  both the measuring case AND a `fontStatus: 'resolved'` laid-out case; `laidOut.test.ts` holds
  a laid-out case. Read as filenames alone the seam is unambiguously phase-based — the exact
  reading the measuring header spends a paragraph denying. The names route the next contributor
  wrongly in two directions: the chartered `'failed'` arm is a FONT-GATE case that belongs with
  the shared binding but has no home by filename, and any future laid-out case reads as
  belonging in `laidOut.test.ts`. The first misapplication is the dangerous one — pulling the
  resolved row out of `measuring.test.ts` because it "is laid-out" re-opens the
  discard-the-argument mutation the split exists to preserve the kill for. The correction lives
  only in prose inside the files, not in their names. Rename to name the subject (the font gate
  / the geometry), and adopt `/refactor`'s forward rule with it: **`measuring.test.ts` is closed
  at 192 lines — it holds the font gate and nothing else, and no new case joins it.** Each
  pending step then pays for its own header in its own file (`paginationState.failed.test.ts`
  and so on) and the 8 lines of headroom never have to be rationed.
- [ ] red-frontend (agent-review CONCERNS 3 over `2572b8be`) — **scenario provenance is
  orphaned in the sibling.** `laidOut.test.ts` asserts `paginationStatusText: ''`,
  `measuringMessage: ''`, `liveRegionRole: null`, `ariaBusy: false` — product-defined values
  whose entire justification (the two-node `pagination-status` / `page-count` split,
  `pagination_measuring_statements.py:88-91`, the `red-selenium` vocabulary, and 1.1's own
  Given/When/Then) exists only in `measuring.test.ts`. Its sole link is "for the same reason
  both cases in the sibling file are". One hop today — but it points into the file already
  flagged for a further split, after which it points at a paragraph that may not be there, with
  nothing that fails. Give the file its own provenance line, or point at the spec rather than at
  a sibling's paragraph.
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
- [ ] red-frontend (premortem CREDIBLE 1 + agent-review CONCERNS 2 over `72d9b438`, the same
  defect from both sides) — **`Страница 7 из 3`: the two halves of one reading now have two
  producers and no stated relationship.** `pageCount` is DERIVED (`ceil` over the geometry);
  `currentPage` is PASSED THROUGH. `visiblePageNumber: number` is unconstrained — the type
  admits `0`, `-1`, `2.4`, and anything greater than `pageCount` — and neither the interface
  nor either case says whether `derivePaginationState` clamps or whether an out-of-range
  viewport is the caller's bug. "1-based" is a doc comment, not a guard. Incident: a reader on
  page 7 of a 12-page document deletes three-quarters of the text; it re-paginates to 3
  sheets, the scroll container clamps to the new bottom, and the status bar reads
  `Страница 7 из 3`. Same shape on every font-size change, every sidebar toggle that changes
  `usableContentHeight`, and any frame where the caller's scroll observation lands one tick
  before the re-layout. The widened varying-geometry step does NOT close this: it asks for a
  second *consistent, in-range* value, which kills the arithmetic-hop mutants and leaves a
  pure pass-through green. Guard: a laid-out case whose fixture supplies a `visiblePageNumber`
  GREATER than the `pageCount` the same fixture derives (e.g. `9` against the 4-sheet
  document), asserting the decided outcome — clamp to `pageCount`, `null`, or a stated
  pass-through — plus the interface doc stating which; a sibling case for `0` or a
  non-integer if the answer is clamp.
- [ ] red-frontend (premortem CREDIBLE 2 over `72d9b438`) — **the hardcoded `1` was not
  killed, it was promoted one layer up, into a layer no chartered step tests.** The commit
  message and the step above both acknowledge the relocation and both home it to the
  `green-frontend` component test. **That home cannot hold it.** A component test renders a
  component GIVEN a `PaginationViewState`, so its fixture supplies `currentPage` directly and
  never exercises the producer; `visiblePageNumber` is upstream of `derivePaginationState`.
  Grep confirms it: `visiblePageNumber` appears in exactly two files, and `scroll` appears
  nowhere in `acceptance/statements/frontend/editor/` or `acceptance/tests/frontend/editor/`.
  2.1 owns where breaks FALL, 2.2 owns per-sheet numbers — **no scenario owns "which sheet is
  in view."** Incident: green ships, vitest green, component test green, `align-design` passes,
  `green-selenium` passes (its assertion is the measuring phase's ABSENCE of `page-count`), and
  a reader scrolling to sheet 5 still reads `Страница 1 из 12` — the exact defect this unit
  exists to prevent, invisible to every test named in this file. Guard: a named step with an
  owner for the scroll→`visiblePageNumber` producer, naturally a Selenium assertion that
  scrolling the laid-out editor moves `page-count` from `Страница 1 из N` to `Страница 2 из N`.
  Only the browser leg can make that claim.
- [ ] red-frontend (agent-review CONCERNS 1 over `72d9b438`) — **the input side does not model
  absence, so no test can ever pin the unknown-viewport case.** `visiblePageNumber` is a
  required non-nullable `number`, but the measuring phase is exactly the state in which no
  such number exists: there are no sheets, only one skeleton, and the caller has nothing to
  observe. The diff demonstrates it — `AMPLY_MEASURABLE_DOCUMENT` supplies `2` and is spread
  into the `fontStatus: 'pending'` call, asserting the module is handed "the reader is on
  sheet 2" for a document that has not been laid out. The output side models absence
  (`currentPage: number | null`, `pageCount: number | null`); the input side does not, so every
  measuring-phase caller must fabricate a value and the type forbids any test from pinning
  what happens when the viewport is unknown. The natural fix — `visiblePageNumber: number |
  null` with a measuring row supplying `null` — trades away the pass-through kill the header
  comment leans on, so this needs a DECISION, not a silent widening. Premortem rated the same
  asymmetry REMOTE on the grounds that `currentPage: null` absorbs whatever the caller
  invents; agent-review rates it now because the *unpinnable* half survives that absorption.
- [ ] red-frontend (agent-review CONCERNS 3 over `72d9b438`) — **the retracted over-claim
  survives one field away.** This unit narrowed the interface header from "the count is carried
  by `pageCount` as a NUMBER and by nothing else" precisely because the reading holds two
  numbers — but `paginationStatusText`'s doc twelve lines below still reads "the only thing
  pagination has to say is the count and the count is `pageCount` rendered by `page-count`",
  the same one-number claim in the same interface, untouched; likewise the surviving test-file
  line "The count is carried by `pageCount` as a number and by…". A reader landing on the
  `paginationStatusText` doc gets the pre-commit model. Comment-only, no behavior — fold into
  the next unit that touches the file, which is also the split unit.
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
  Green's deliverable was originally stated as a whole-suite skip count ("3 skipped, not 5",
  then "not SIX" after the split). **That formulation is WITHDRAWN — it is not a guard**
  (premortem CREDIBLE 1 over `2572b8be`). A whole-suite count is
  `pagination_skips + manual_editor_skips`, and the second term is not a constant: those are
  three `it.skip` RED rows awaiting their own green steps
  (`ManualEditor.autosaveAbandonFalseRecord.test.tsx:76,154`,
  `ManualEditor.autosaveAbandonRecord.test.tsx:167`). The arithmetic fails both ways — one
  autosave row going green gives `2 + 1 = 3` with `paginationState.laidOut.test.ts` STILL
  DARK, so the number is satisfied by exactly the failure it was written to catch; and any new
  RED row anywhere under `frontend/src` makes green look failed when it succeeded. Coverage
  does not backstop it either: the laid-out branch is exercised by the measuring file's second
  case, so `scripts/check-per-file-coverage.mjs` and the `vite.config.ts` thresholds stay green
  with `laidOut.test.ts` skipped.
  **The deliverable is a SCOPED ZERO instead:** after green, `frontend/src/features/editor/
  logic/__tests__/` contains no `it.skip` and no `describe.skip` — a grep over that directory,
  or a vitest run filtered to `paginationState` reporting `0 skipped`. That is invariant under
  every autosave step and every unrelated future RED row. Green must unskip **two files**
  (`paginationState.measuring.test.ts` and `paginationState.laidOut.test.ts`); the second is
  the easier to forget, and forgetting it reinstates the constant-return green this chain
  exists to prevent.
  **Second green deliverable, equally verifiable** (premortem CREDIBLE 3 over `2572b8be`):
  green's diff over `frontend/src/features/editor/logic/__tests__/**` must consist SOLELY of
  `it.skip` → `it`. "Tests are read-only in green" is an agent-instruction convention, not a
  check, and the new file is the natural place for a violation to hide: it is the harder of
  the two to make pass (it demands a real packer, where the measuring rows tolerate a
  `fontStatus` branch), its expected `6`/`5` sit in one inline literal with the fixture three
  lines above, its input is an anonymous object literal rather than a named typed constant —
  the cheapest thing in the pair to nudge — and no other case in that file cross-checks it.
  Nudging `usableContentHeight: 600` to `700` to make an implementation pass would leave the
  suite green and `0 skipped` intact. Stated as a diff check, that becomes a finding instead
  of a non-event.
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
