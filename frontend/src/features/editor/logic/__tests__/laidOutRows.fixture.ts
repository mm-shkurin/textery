/**
 * The two laid-out rows — each row's GEOMETRY and the `(pageCount, currentPage)` pair that geometry
 * is expected to produce — plus the candidate wrong derivations of each expected number that
 * scenario 1.1 has ruled out.
 *
 * WHY THE NUMBERS LIVE HERE AND NOT IN THE TEST FILES. `currentPage` is a pass-through and
 * `pageCount` is derived, so every plausible wrong implementation is some hop from one value to
 * another: `currentPage` from `pageCount` (`pageCount`, `pageCount - 1`, `pageCount / 2`, a hardcoded
 * `1`), or `pageCount` from something that is not the geometry at all (`blockHeights.length`, a
 * skeleton constant, the other expected number of the same row). A single laid-out row cannot refute
 * all of them — every expected number is an arithmetic hop from every other one — so each hop has to
 * die across the PAIR of rows. That makes the two rows a single invariant held jointly, and the split
 * into `paginationState.measuring.test.ts` (the font gate) and `paginationState.laidOut.test.ts` (the
 * geometry) put the two halves on different screens, where only header prose said they depended on
 * each other. `paginationState.crossRow.test.ts` turns that prose into a check; this module is what
 * gives it something to check.
 *
 * WHY THE GEOMETRY MOVED IN TOO, AND IS NOT MERELY DESCRIBED HERE. An earlier version of this module
 * held `pageCount: 4` while describing "seven blocks totalling 2800px against 900px" in the header of
 * a file containing neither `blockHeights` nor `usableContentHeight` — the derivation was a comment
 * spanning two other files, which is precisely the defect this module was created to end, reproduced
 * one field over. Three chartered steps are queued to edit that geometry; any of them could retune it
 * and leave `pageCount` stale, with every case that would notice `.skip`ped for the whole RED phase.
 * With the geometry here, `paginationState.crossRow.test.ts` derives each row's `pageCount` from that
 * row's own blocks and fails on the spot when one moves without the other.
 *
 * WHY `4` FOR THE FONT-GATE ROW and `6` FOR THE VARIED-GEOMETRY ROW. Neither is chosen; each is what
 * its own geometry produces (`ceil(2800 / 900)` and `ceil(3600 / 600)`), which is why both are now
 * asserted rather than asserted-about. Both counts are PACKING-AGNOSTIC, which is what keeps scenario
 * 2.1's choice of where breaks FALL open: greedy no-split packing agrees with split-anywhere on both
 * documents (`400+380 | 420+390 | 410+400 | 400` = 4; `400+200 | 300+300 | 600 | 250+350 | 600 |
 * 100+300+200` = 6). That agreement is asserted for `ceil` only below — pinning BOTH candidate
 * packers is a separate chartered step, and this module does not pre-empt it.
 *
 * WHY `2` FOR THE FONT-GATE ROW'S `currentPage`. It is not `1`, the literal a component types when
 * "Страница N из M" has no source for its N — the readout that never moves as the reader scrolls, and
 * the defect `currentPage` exists to make fail. It is not `4`, so `currentPage: pageCount` — a readout
 * permanently pinned to the last sheet — dies too.
 *
 * WHY `5` FOR THE VARIED-GEOMETRY ROW. The same exclusions restated against that row's `6`: not `6`,
 * not `3`, not `1`. It is in range (`5 <= 6`) deliberately — whether an out-of-range viewport clamps,
 * nulls, or passes through is an open question with its own chartered step, and answering it by
 * accident here would decide it in silence.
 *
 * Concretely on the cross-row half: `5` is `6 - 1`, so the varied-geometry row cannot refute the
 * 0-based/1-based off-by-one on its own. It dies only because the font-gate row expects `2` where
 * `4 - 1` is `3`. Retune EITHER row so the two agree under `p - 1` and that hop becomes live
 * implementation behaviour — which is exactly the state this module exists to end.
 *
 * Each test file still keeps its own whole-object expectation and its own header, and the font-gate
 * file's two cases stay driven over ONE local binding built from this row, which is what kills a
 * `derivePaginationState` that discards its argument. Each file also derives its `visiblePageNumber`
 * from its own row's `currentPage` rather than repeating the number, so the supplied viewport and the
 * expected readout cannot drift apart — the pass-through pin, mechanical instead of a coincidence of
 * two literals.
 */

export interface LaidOutRow {
  /** How `paginationState.crossRow.test.ts` names this row in its refutation matrices. */
  readonly name: string
  /** Measured block heights this row's document is laid out from, in CSS pixels. */
  readonly blockHeights: readonly number[]
  /** Height available for content on one sheet, in CSS pixels. */
  readonly usableContentHeight: number
  /** The "M" of "Страница N из M" — total sheets, DERIVED from this row's own geometry above. */
  readonly pageCount: number
  /** The "N" — the sheet in view, PASSED THROUGH from this row's `visiblePageNumber`. */
  readonly currentPage: number
}

/** Drives both font-gate cases in `paginationState.measuring.test.ts`. */
export const FONT_GATE_ROW: LaidOutRow = {
  name: 'the font-gate row',
  blockHeights: [400, 380, 420, 390, 410, 400, 400],
  usableContentHeight: 900,
  pageCount: 4,
  currentPage: 2,
}

/** Drives `paginationState.laidOut.test.ts`. */
export const VARIED_GEOMETRY_ROW: LaidOutRow = {
  name: 'the varied-geometry row',
  blockHeights: [400, 200, 300, 300, 600, 250, 350, 600, 100, 300, 200],
  usableContentHeight: 600,
  pageCount: 6,
  currentPage: 5,
}

export const LAID_OUT_ROWS: readonly LaidOutRow[] = [FONT_GATE_ROW, VARIED_GEOMETRY_ROW]

/**
 * The count a split-anywhere packer answers: the theoretical lower bound on sheets, and the bound
 * greedy no-split ACHIEVES on both rows above. Deriving each row's declared `pageCount` from this
 * makes retuning a row's geometry without its count fail, and `pageCount: blockHeights.length` fail.
 */
export const splitAnywherePageCount = (row: LaidOutRow): number =>
  Math.ceil(row.blockHeights.reduce((total, height) => total + height, 0) / row.usableContentHeight)

export interface CurrentPageHop {
  readonly name: string
  readonly derive: (pageCount: number) => number
}

/**
 * Implementations of `currentPage` that never read `visiblePageNumber` at all. Each is a real thing
 * someone writes; each is refuted by at least one row above, and the cross-row test pins WHICH.
 */
export const RULED_OUT_CURRENT_PAGE_HOPS: readonly CurrentPageHop[] = [
  { name: 'pageCount', derive: (pageCount) => pageCount },
  { name: 'pageCount - 1', derive: (pageCount) => pageCount - 1 },
  { name: 'pageCount / 2', derive: (pageCount) => pageCount / 2 },
  { name: '1', derive: () => 1 },
]

/**
 * The fixed design constants of the rendered surfaces, named here ONLY so a row's numbers can be
 * refuted against them. They are not the expectations — each test file still spells its own skeleton
 * counts out at its own assertion. `railSkeletonCount: 3` colliding with a three-block
 * `blockHeights.length` is not hypothetical: it shipped in this scenario once and was caught by
 * review rather than by a test.
 */
export const SURFACE_CONSTANTS: Readonly<Record<string, number>> = {
  'the measuring surface’s one skeleton sheet': 1,
  'the measuring surface’s three rail rows': 3,
  'the laid-out phase’s zero skeletons': 0,
}

/**
 * The numbers a row's expectations are stated in that belong to THAT row — the ones a retune of the
 * row moves. Kept separate from `SURFACE_CONSTANTS` because the cross-row check compares one row's
 * numbers against the other's, and the constants are shared: included there, every row would collide
 * with every other row on `1`, `3` and `0` and the check would report nothing but noise.
 */
export const rowValuesOf = (row: LaidOutRow): Readonly<Record<string, number>> => ({
  pageCount: row.pageCount,
  currentPage: row.currentPage,
  'blockHeights.length': row.blockHeights.length,
})

/**
 * Every number a row's expectations are stated in, by name, for the SAME-row collision check. Two
 * entries sharing a value mean some field of that row can be satisfied by echoing another — the
 * failure mode that makes a wrong implementation green on this fixture and wrong on every real
 * document. The other half of that claim — that a row's numbers are unreachable from the OTHER row's,
 * which is what kills a frozen literal carried across rows — is `rowValuesOf` compared pairwise.
 */
export const namedValuesOf = (row: LaidOutRow): Readonly<Record<string, number>> => ({
  ...SURFACE_CONSTANTS,
  ...rowValuesOf(row),
})
