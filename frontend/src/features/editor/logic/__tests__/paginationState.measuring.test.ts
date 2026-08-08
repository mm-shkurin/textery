import { describe, expect, it } from 'vitest'
import { derivePaginationState } from '../paginationState'

/**
 * Story 10, UI scenario 1.1 — "Pagination waits for the document font".
 *
 *   Given a document is opened and the document font has not finished loading
 *   When the editor is displayed
 *   Then the measuring state is shown
 *   And no page count is displayed
 *   And the state is visibly distinct from an error and from an empty document
 *
 * Heights are SUPPLIED and they are amply sufficient to lay the document out (seven blocks
 * totalling 2800px against 900px of usable sheet — four pages' worth, whichever way they pack).
 * That is the point of the case: having measurements is not permission to paginate. The font gate
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
 * Counts, copy, and attribute values are the ones `red-selenium` pinned in
 * `acceptance/statements/frontend/editor/pagination_measuring_locators.py` — one skeleton sheet,
 * exactly three rail rows, `role="status"`, `aria-busy="true"`, and the two product-defined strings
 * `EXPECTED_MEASURING_STATUS` / `EXPECTED_MEASURING_MESSAGE`. Same state, same vocabulary. The
 * status copy carries real weight for the third Then: "Расчёт страниц…" is precisely what the empty
 * document does NOT say, where it reads "Страница 1 из 1" against an identical single sheet.
 */
describe('derivePaginationState — the document font has not resolved', () => {
  // TDD RED — fails with `Error: Not implemented` at paginationState.ts:51. `derivePaginationState`
  // is a stub; no pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('holds the editor in the measuring state with no page count, however measurable the document is', () => {
    const state = derivePaginationState({
      fontStatus: 'pending',
      blockHeights: [400, 380, 420, 390, 410, 400, 400],
      usableContentHeight: 900,
    })

    expect(state).toEqual({
      phase: 'measuring',
      pageCount: null,
      sheetSkeletonCount: 1,
      railSkeletonCount: 3,
      liveRegionRole: 'status',
      ariaBusy: true,
      statusText: 'Расчёт страниц…',
      measuringMessage: 'Готовим страницы…',
    })
  })
})

/**
 * The counter-case, over the SAME geometry — same `blockHeights`, same `usableContentHeight`.
 * `fontStatus` is the only thing that differs between the two cases, which is what makes it
 * load-bearing: with one case only, every expected field above is a constant, and a
 * `derivePaginationState` that discards its argument and returns a frozen literal passes. That
 * exact mutation was demonstrated. Then the scenario's whole claim — the font gate dominates the
 * geometry — would be asserted by the header comment and by nothing else, and the permanent
 * spinner scenario 1.3 exists to forbid would ship as the implemented behavior.
 *
 * LEAVING the measuring state is pinned the same way ENTERING it is: by comparing the whole state
 * object, minus the one field a later chartered step owns. Asserting `phase` alone would let an
 * implementation flip the discriminant while still emitting `sheetSkeletonCount: 1`,
 * `railSkeletonCount: 3`, `liveRegionRole: 'status'`, `ariaBusy: true` and the measuring copy —
 * a laid-out document with the skeleton surface still up, the spinner still spinning, and a screen
 * reader still told the editor is busy. That is the mirror image of the defect the first case's
 * whole-object comparison exists to forbid ("the right phase alongside a stray page count"), and it
 * is the same family both prior reviews of this scenario found. So the measuring surface is pinned
 * POSITIVELY absent — exact `0` / `null` / `false` / `''`, the values `PaginationViewState`'s own
 * doc comments define for phases that render no such surface — not left unmentioned.
 *
 * `pageCount` is pinned to a value, not to `not.toBeNull()`. Non-null is satisfiable by `0` and by
 * `-1`: an editor claiming to be laid out across zero pages. The count is not opaque here — heights
 * are SUPPLIED, not measured, so 2800px of blocks against 900px of usable sheet is fully determined
 * by this fixture's arguments. `4` also does not pre-empt scenario 2.1, which owns WHERE the breaks
 * fall: greedy no-split packing (400+380 | 420+390 | 410+400 | 400) and split-anywhere packing
 * (`ceil(2800/900)`) agree on 4 for this document, so both of 2.1's candidate answers pass and the
 * choice between them stays open.
 *
 * `statusText` is the ONE field deliberately not compared, and it is excluded by name rather than
 * by silence. The next `red-frontend` step in `progress-frontend.md` is chartered to decide it:
 * `red-selenium` splits the status bar into `pagination-status` and a separate `page-count` node,
 * so whether the laid-out `statusText` carries "Страница 1 из 4" in prose at all is exactly that
 * step's open question. Pinning a value here would answer it in the direction that step suspects is
 * wrong. Every other field is decided now.
 */
describe('derivePaginationState — the document font has resolved', () => {
  // TDD RED — fails with `Error: Not implemented` at paginationState.ts:51. `derivePaginationState`
  // is a stub; no pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('lays the document out and tears the measuring surface down', () => {
    const state = derivePaginationState({
      fontStatus: 'resolved',
      blockHeights: [400, 380, 420, 390, 410, 400, 400],
      usableContentHeight: 900,
    })

    const { statusText: _statusText, ...laidOut } = state
    expect(laidOut).toEqual({
      phase: 'laid-out',
      pageCount: 4,
      sheetSkeletonCount: 0,
      railSkeletonCount: 0,
      liveRegionRole: null,
      ariaBusy: false,
      measuringMessage: '',
    })
  })
})
