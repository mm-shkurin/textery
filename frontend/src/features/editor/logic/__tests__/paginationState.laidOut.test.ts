import { describe, expect, it } from 'vitest'
import { derivePaginationState } from '../paginationState'
import { NO_SKELETONS, VARIED_GEOMETRY_ROW } from './laidOutRows.fixture'

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
 * The fixture. Eleven blocks totalling 3600px against 600px of usable sheet, supplied by
 * `VARIED_GEOMETRY_ROW` rather than typed here — the geometry and the count it produces are one
 * value, and `paginationState.crossRow.test.ts` derives `6` from those blocks and compares it against
 * the row's own declared `pageCount`, so retuning either alone goes red. The count stays
 * PACKING-AGNOSTIC, which is what keeps scenario 2.1's choice of where breaks FALL open: the blocks
 * pack exactly, so greedy no-split (400+200 | 300+300 | 600 | 250+350 | 600 | 100+300+200) and
 * split-anywhere (`ceil(3600/600)`) both answer 6. Only a perfectly-packing fixture has that
 * property, which is why the geometry is spelled out this way rather than picked round.
 *
 * `6` is reachable from no other value in either file — not `4`, not the `1`/`3` skeleton counts,
 * and not `blockHeights.length` (11), so `pageCount: blockHeights.length` still fails. That claim
 * used to be this sentence and nothing else; it is now the second `describe` of
 * `paginationState.crossRow.test.ts`, which enumerates every number this row's expectations are
 * stated in and fails on any collision between them.
 *
 * `visiblePageNumber` is `VARIED_GEOMETRY_ROW.currentPage`, and the pair `(6, 5)` is not this file's
 * to retune alone. No `visiblePageNumber` in range of a 6-page document escapes every arithmetic hop
 * to `6`, so the hops die across the two rows rather than within one: this row kills
 * `currentPage: pageCount / 2` (`3` against `5`), and it SURVIVES `currentPage: pageCount - 1`,
 * because `5` is `6 - 1`. That one — the 0-based/1-based off-by-one, the likeliest accident of the
 * three — is killed only by the sibling file's row, `4 - 1` being `3` against an expected `2`.
 *
 * That dependency used to be this paragraph and nothing else, which meant retuning EITHER row so the
 * pair agreed under `p - 1` shipped the hop as behaviour with nothing red. Both rows' numbers now
 * live in `laidOutRows.fixture.ts`, and `paginationState.crossRow.test.ts` pins the refutation
 * matrix — which hop each row kills, by name — so the pair can no longer stop disagreeing quietly.
 * `5` is in range (`5 <= 6`) deliberately: whether an out-of-range viewport clamps, nulls, or passes
 * through is an open question with its own chartered step, and answering it by accident here would
 * decide it in silence.
 *
 * The state is compared whole, `toStrictEqual`, for the same reason both cases in the sibling file
 * are: the measuring surface must be pinned POSITIVELY absent — exact `0` / `0` / `null` / `false` /
 * `''` — or an implementation could lay the document out with the skeletons still up and the screen
 * reader still told the editor is busy. The two zeros are read as `NO_SKELETONS` so that the value
 * the same-row collision check refutes against and the value asserted here are one declaration; the
 * NUMBER those assertions pin is still `0`, and that is decided here rather than by the binding's
 * name. Change `NO_SKELETONS` to anything else and the laid-out zero collides with the measuring
 * surface's `1` in `paginationState.crossRow.test.ts`, which is LIVE today.
 */
describe('derivePaginationState — a resolved font over different geometry', () => {
  // TDD RED — fails with `Error: Not implemented`; `derivePaginationState` is a stub and no
  // pre-layout state machine exists in `frontend/src` yet. Unskip in green-frontend.
  it.skip('derives the page count and the visible page from the geometry it is handed, not from constants', () => {
    const state = derivePaginationState({
      fontStatus: 'resolved',
      blockHeights: [...VARIED_GEOMETRY_ROW.blockHeights],
      usableContentHeight: VARIED_GEOMETRY_ROW.usableContentHeight,
      visiblePageNumber: VARIED_GEOMETRY_ROW.currentPage,
    })

    expect(state).toStrictEqual({
      phase: 'laid-out',
      pageCount: VARIED_GEOMETRY_ROW.pageCount,
      currentPage: VARIED_GEOMETRY_ROW.currentPage,
      sheetSkeletonCount: NO_SKELETONS,
      railSkeletonCount: NO_SKELETONS,
      liveRegionRole: null,
      ariaBusy: false,
      paginationStatusText: '',
      measuringMessage: '',
    })
  })
})
