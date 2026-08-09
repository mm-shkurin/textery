import { describe, expect, it } from 'vitest'
import { derivePaginationState, type PaginationInput } from '../paginationState'

/**
 * The geometry both cases below are driven over — seven blocks totalling 2800px against 900px of
 * usable sheet, four pages' worth whichever way they pack. It is a single binding rather than two
 * literals BECAUSE the two cases must be byte-identical here: `fontStatus` being the only differing
 * input is what makes the font gate load-bearing, and a shared binding enforces that instead of
 * asking a reader to diff two arrays and take the header comments' word for it.
 *
 * Only the INPUT is shared. Every expected field stays spelled out at its own assertion — the
 * whole-object comparisons exist to make each one visible, and no fixture value may be reachable
 * from an expected value it does not BELONG to. `currentPage` is the one deliberate exception, and
 * it is the point rather than a slip: which sheet is in view is a viewport fact this module is
 * handed, so the laid-out case expecting exactly the `2` the fixture supplies is what pins the
 * pass-through. Every OTHER field must still fail if it echoes a fixture value.
 *
 * `visiblePageNumber` is **2** and the choice is load-bearing three times over. It is not `1`,
 * which is the literal a component renders when "Страница N из M" has no source for its N — the
 * exact readout that never moves as the reader scrolls, and the defect this input exists to make
 * fail. It is not `4` either, so `currentPage: pageCount` (a readout permanently pinned to the last
 * sheet) dies too. And it collides with no OTHER field's expected value — not the `1` and `3`
 * skeleton counts below, not `blockHeights.length` (7), not the laid-out `4` — so no other field
 * can be satisfied by echoing it.
 *
 * What `2` does NOT kill, stated plainly rather than left for a later reader to discover: with one
 * laid-out case, `currentPage` and `pageCount` are two numbers in one object, and `2` is `4 / 2`.
 * `currentPage: pageCount / 2` passes both cases (the measuring case early-returns on the phase
 * discriminant and never evaluates it). No literal in `1..4` escapes this — `1` is `pageCount - 3`,
 * `3` is `pageCount - 1`, `4` is `pageCount` — because a single fixture makes every expected number
 * an arithmetic hop from every other. Only a second laid-out row with a DIFFERENT
 * `visiblePageNumber` against a different `pageCount` closes it, which is the varying-geometry step
 * already chartered in `progress-frontend.md`; that step must vary this input too, not the geometry
 * alone. It is recorded there, not deferred silently here.
 */
const AMPLY_MEASURABLE_DOCUMENT: Omit<PaginationInput, 'fontStatus'> = {
  blockHeights: [400, 380, 420, 390, 410, 400, 400],
  usableContentHeight: 900,
  visiblePageNumber: 2,
}

/**
 * Story 10, UI scenario 1.1 — "Pagination waits for the document font".
 *
 *   Given a document is opened and the document font has not finished loading
 *   When the editor is displayed
 *   Then the measuring state is shown
 *   And no page count is displayed
 *   And the state is visibly distinct from an error and from an empty document
 *
 * Heights are SUPPLIED and they are amply sufficient to lay the document out (see
 * `AMPLY_MEASURABLE_DOCUMENT` above). That is the point of the case: having measurements is not
 * permission to paginate. The font gate
 * dominates, because heights measured against a substituted face would produce a count that
 * changes under the user once the real face arrives (scenario 1.2's "does not change again on its
 * own"). A `derivePaginationState` that looked only at the geometry would return a laid-out page
 * count here and pass nothing.
 *
 * The geometry is chosen so that NO expected value is reachable by computing on the input. The
 * document has 7 blocks and lays out to 4 pages; the expected counts are 1 and 3. So
 * `railSkeletonCount: blockHeights.length` (7) and `sheetSkeletonCount: ceil(sum/usable)` (4) both
 * fail — the rail's three rows and the single skeleton sheet are pinned as the design constants
 * they are, not as coincidences of this fixture. An earlier fixture used three blocks summing to
 * one page's worth, where both wrong implementations passed.
 *
 * The third Then is pinned POSITIVELY, not by absence — that exact defect was found by
 * `/test-review` on this scenario's Selenium leg. `phase` is a discriminant that is neither
 * `'error'` nor `'laid-out'`, and the skeleton counts plus the live-region attributes are the
 * things the error state (an error surface) and the empty document (a real, blank sheet) do not
 * render. The whole state object is compared, so an implementation cannot satisfy the scenario by
 * emitting the right phase alongside a stray page count.
 *
 * The second Then — "no page count is displayed" — now has TWO numbers to be absent, and both are
 * asserted `null`. `currentPage: null` is the strictly stronger of the pair here: the fixture
 * SUPPLIES `visiblePageNumber: 2`, so an implementation that passes the viewport straight through
 * without consulting `fontStatus` — the shortest thing anyone would write — emits `2` and fails.
 * The field is a number the caller hands in, which is exactly why leaving it unmentioned would let
 * the count half of the count reading survive the measuring phase.
 *
 * Counts, copy, and attribute values are the ones `red-selenium` pinned in
 * `acceptance/statements/frontend/editor/pagination_measuring_locators.py` — one skeleton sheet,
 * exactly three rail rows, `role="status"`, `aria-busy="true"`, and the two product-defined strings
 * `EXPECTED_MEASURING_STATUS` / `EXPECTED_MEASURING_MESSAGE`. Same state, same vocabulary. The
 * status copy carries real weight for the third Then: "Расчёт страниц…" is precisely what the empty
 * document does NOT say, where its own count node reads "Страница 1 из 1" against an identical
 * single sheet.
 */
describe('derivePaginationState — the document font has not resolved', () => {
  // TDD RED — fails with `Error: Not implemented`; `derivePaginationState` is a stub and no
  // pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('holds the editor in the measuring state with no page count, however measurable the document is', () => {
    const state = derivePaginationState({ fontStatus: 'pending', ...AMPLY_MEASURABLE_DOCUMENT })

    expect(state).toStrictEqual({
      phase: 'measuring',
      pageCount: null,
      currentPage: null,
      sheetSkeletonCount: 1,
      railSkeletonCount: 3,
      liveRegionRole: 'status',
      ariaBusy: true,
      paginationStatusText: 'Расчёт страниц…',
      measuringMessage: 'Готовим страницы…',
    })
  })
})

/**
 * The counter-case, over the same `AMPLY_MEASURABLE_DOCUMENT` binding the first case is driven
 * over, so `fontStatus` is the only thing that CAN differ between the two — which is what makes it
 * load-bearing: with one case only, every expected field above is a constant, and a
 * `derivePaginationState` that discards its argument and returns a frozen literal passes. That
 * exact mutation was demonstrated. Then the scenario's whole claim — the font gate dominates the
 * geometry — would be asserted by the header comment and by nothing else, and the permanent
 * spinner scenario 1.3 exists to forbid would ship as the implemented behavior.
 *
 * LEAVING the measuring state is pinned the same way ENTERING it is: by comparing the whole state
 * object — every field of it, no exclusions. Asserting `phase` alone would let an
 * implementation flip the discriminant while still emitting `sheetSkeletonCount: 1`,
 * `railSkeletonCount: 3`, `liveRegionRole: 'status'`, `ariaBusy: true` and the measuring copy —
 * a laid-out document with the skeleton surface still up, the spinner still spinning, and a screen
 * reader still told the editor is busy. That is the mirror image of the defect the first case's
 * whole-object comparison exists to forbid ("the right phase alongside a stray page count"), and it
 * is the same family both prior reviews of this scenario found. So the measuring surface is pinned
 * POSITIVELY absent — exact `0` / `null` / `false` / `''` — not left unmentioned. Two of those
 * follow from `PaginationViewState`'s own doc comments (`liveRegionRole` is `null` where no live
 * region is rendered; `measuringMessage` belongs to the measuring surface). The skeleton counts do
 * NOT: `sheetSkeletonCount` carries no doc comment and `railSkeletonCount`'s describes only the
 * measuring surface's fixed three rows. `0` for a phase that renders no skeletons is decided HERE,
 * not restated from the interface.
 *
 * `pageCount` is pinned to a value, not to `not.toBeNull()`. Non-null is satisfiable by `0` and by
 * `-1`: an editor claiming to be laid out across zero pages. The count is not opaque here — heights
 * are SUPPLIED, not measured, so 2800px of blocks against 900px of usable sheet is fully determined
 * by this fixture's arguments. `4` also does not pre-empt scenario 2.1, which owns WHERE the breaks
 * fall: greedy no-split packing (400+380 | 420+390 | 410+400 | 400) and split-anywhere packing
 * (`ceil(2800/900)`) agree on 4 for this document, so both of 2.1's candidate answers pass and the
 * choice between them stays open.
 *
 * `currentPage: 2` pins the OTHER number. `01-editor-paginated.html:96` reads "Страница 1 из 3":
 * two numbers, and until now the view state carried one. `pageCount` is the "M"; nothing was the
 * "N", and the whole-object comparison had frozen the field set with no member for it — so the only
 * green this test admitted was `Страница 1 из {pageCount}` with a hardcoded literal, a readout that
 * is right on the first sheet and wrong on every other one, with nothing anywhere able to fail on
 * it. Expecting `2` where the fixture supplies `2` makes that literal fail, and expecting a number
 * distinct from `pageCount` makes "always the last sheet" fail as well.
 *
 * It is likewise `2` and not `null` here for the reason `pageCount` is `4` and not merely non-null:
 * the reading has two halves and a half-absent one ("Страница  из 4") is not a state the mockup
 * shows. It stays packing-agnostic — which sheet is in view is supplied by the caller, so this test
 * says nothing about where the breaks fall, and 2.1's choice is untouched.
 *
 * `paginationStatusText` was the ONE field left open, excluded by name from the comparison above so
 * that this step could decide it rather than have it decided by silence. It is decided now, and the
 * whole state object is compared: **`''`**. The count is carried by `pageCount` as a number and by
 * nothing else.
 *
 * That is the direction `red-selenium` already committed to and it is not a free choice. The status
 * bar is TWO nodes — `pagination-status` and a separate `page-count` — and
 * `pagination_measuring_statements.py:88-91` names why: "a missing `page-count` node with a status
 * bar already reading 'Страница 1 из 1' would satisfy a pure absence check while telling the user a
 * page count in prose." A `paginationStatusText` of "Страница 1 из 4" is exactly that failure,
 * authored into the view state rather than stumbled into by a component: the count would be held
 * TWICE, once as a number and once as prose, and the absence assertion the scenario's second Then
 * rests on would be satisfiable while the user reads a count. `''` makes the prose copy
 * unrepresentable — there is no string left for a component to render into the wrong node.
 *
 * `''` is a decision about the pagination module's contract, not a claim that the laid-out status
 * bar is blank. `01-editor-paginated.html:95-96` shows that slot holding "415 слов · Все изменения
 * сохранены" — word count and save state, which belong to other features and reach the bar by their
 * own fields. Pagination contributes phase prose while it has something to say and nothing once the
 * pages exist, exactly as `measuringMessage` does; the two fields now go empty together, which is
 * what "tears the measuring surface down" means.
 */
describe('derivePaginationState — the document font has resolved', () => {
  // TDD RED — fails with `Error: Not implemented`; `derivePaginationState` is a stub and no
  // pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('lays the document out and tears the measuring surface down, leaving the count to the count node', () => {
    const state = derivePaginationState({ fontStatus: 'resolved', ...AMPLY_MEASURABLE_DOCUMENT })

    expect(state).toStrictEqual({
      phase: 'laid-out',
      pageCount: 4,
      currentPage: 2,
      sheetSkeletonCount: 0,
      railSkeletonCount: 0,
      liveRegionRole: null,
      ariaBusy: false,
      paginationStatusText: '',
      measuringMessage: '',
    })
  })
})
