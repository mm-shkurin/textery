import { describe, expect, it } from 'vitest'
import { derivePaginationState } from '../paginationState'

/**
 * Story 10, UI scenario 1.1 — the second laid-out row, over DIFFERENT geometry.
 *
 * Why it is a separate file. `paginationState.measuring.test.ts` holds the font gate: two cases
 * driven over ONE shared binding, so `fontStatus` is the only input that can differ between them.
 * That co-location is load-bearing — it is what kills a `derivePaginationState` that discards its
 * argument — and folding a varied-geometry row into that file would dissolve the very thing the
 * shared binding asserts. So the seam is by SUBJECT, not by phase: the gate there, the geometry
 * here.
 *
 * What this row exists to kill, both demonstrated by mutation rather than argued. With one laid-out
 * case only, closing the gate on `fontStatus` left every geometry argument exactly where
 * `fontStatus` was before it:
 *
 *   (a) `if (input.fontStatus !== 'pending') return { …pageCount: 4, currentPage: 2… }` — a frozen
 *       literal one branch up, reading neither `blockHeights` nor `usableContentHeight` — passed
 *       both cases in that file. `4` was argued safe BECAUSE both candidate packings agree on it,
 *       and agreement is precisely what makes one fixture unable to tell a packer from a constant.
 *   (b) `currentPage: pageCount / 2` passed both cases too, since `2` is `4 / 2`.
 *
 * Both die here, because this row's expected numbers are unreachable from that file's: the
 * frozen literal emits `4`/`2` where this expects `6`/`5`, and the arithmetic hop emits `3`.
 *
 * The fixture. Eleven blocks totalling 3600px against 600px of usable sheet. The count stays
 * PACKING-AGNOSTIC, which is what keeps scenario 2.1's choice of where breaks FALL open: the blocks
 * pack exactly, so greedy no-split (400+200 | 300+300 | 600 | 250+350 | 600 | 100+300+200) and
 * split-anywhere (`ceil(3600/600)`) both answer 6. Only a perfectly-packing fixture has that
 * property, which is why the geometry is spelled out this way rather than picked round.
 *
 * `6` is reachable from no other value in either file — not `4`, not the `1`/`3` skeleton counts,
 * and not `blockHeights.length` (11), so `pageCount: blockHeights.length` still fails.
 *
 * `visiblePageNumber: 5` is chosen against the same exclusions as the other row's `2`, restated
 * against THIS row's numbers: not `6`, so `currentPage: pageCount` dies; not `3`, so
 * `currentPage: pageCount / 2` dies; not `1`, the literal a component types when "Страница N из M"
 * has no source for its N; and `5` appears as no other expected value anywhere in the pair of
 * files, so no field can be satisfied by echoing it. It is in range (`5 <= 6`) deliberately —
 * whether an out-of-range viewport clamps, nulls, or passes through is an open question with its own
 * chartered step, and answering it by accident here would decide it in silence.
 *
 * One exclusion this row canNOT make on its own, stated here rather than left to be discovered:
 * `5` is `6 - 1`, so `currentPage: pageCount - 1` — the 0-based/1-based off-by-one, the likeliest
 * accident of the three — passes THIS row. It is killed by the sibling file's resolved row, where
 * `4 - 1` is `3` against an expected `2`. The pair closes it; neither file closes it alone. That is
 * the cost of the seam and it is paid knowingly: no `visiblePageNumber` in range of a 6-page
 * document escapes some arithmetic hop to `6`, so the hop has to die across rows rather than within
 * one, exactly as `pageCount / 2` had to.
 *
 * The state is compared whole, `toStrictEqual`, for the same reason both cases in the sibling file
 * are: the measuring surface must be pinned POSITIVELY absent (`0`/`0`/`null`/`false`/`''`), or an
 * implementation could lay the document out with the skeletons still up and the screen reader still
 * told the editor is busy.
 */
describe('derivePaginationState — a resolved font over different geometry', () => {
  // TDD RED — fails with `Error: Not implemented`; `derivePaginationState` is a stub and no
  // pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('derives the page count and the visible page from the geometry it is handed, not from constants', () => {
    const state = derivePaginationState({
      fontStatus: 'resolved',
      blockHeights: [400, 200, 300, 300, 600, 250, 350, 600, 100, 300, 200],
      usableContentHeight: 600,
      visiblePageNumber: 5,
    })

    expect(state).toStrictEqual({
      phase: 'laid-out',
      pageCount: 6,
      currentPage: 5,
      sheetSkeletonCount: 0,
      railSkeletonCount: 0,
      liveRegionRole: null,
      ariaBusy: false,
      paginationStatusText: '',
      measuringMessage: '',
    })
  })
})
