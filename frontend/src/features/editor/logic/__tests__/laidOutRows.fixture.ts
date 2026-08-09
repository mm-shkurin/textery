/**
 * The two laid-out rows' `(pageCount, currentPage)` pairs, and the candidate derivations of the
 * second from the first that scenario 1.1 has ruled out.
 *
 * WHY THE NUMBERS LIVE HERE AND NOT IN THE TEST FILES. `currentPage` is a pass-through and
 * `pageCount` is derived, so every plausible wrong implementation is some arithmetic hop from one to
 * the other: `pageCount`, `pageCount - 1`, `pageCount / 2`, a hardcoded `1`. A single laid-out row
 * cannot refute all of them — every expected number is an arithmetic hop from every other one — so
 * each hop has to die across the PAIR of rows. That makes the two rows' numbers a single invariant
 * held jointly, and the split into `paginationState.measuring.test.ts` (the font gate) and
 * `paginationState.laidOut.test.ts` (the geometry) put the two halves on different screens, where
 * only header prose said they depended on each other. `paginationState.crossRow.test.ts` turns that
 * prose into a check; this module is what gives it something to check.
 *
 * Concretely: `5` is `6 - 1`, so the varied-geometry row cannot refute the 0-based/1-based
 * off-by-one on its own. It dies only because the font-gate row expects `2` where `4 - 1` is `3`.
 * Retune EITHER row so the two agree under `p - 1` and that hop becomes live implementation
 * behaviour with nothing red anywhere — which is exactly the state this module exists to end.
 *
 * WHY `2` FOR THE FONT-GATE ROW. It is not `1`, the literal a component types when "Страница N из M"
 * has no source for its N — the readout that never moves as the reader scrolls, and the defect
 * `currentPage` exists to make fail. It is not `4`, so `currentPage: pageCount` — a readout
 * permanently pinned to the last sheet — dies too. And it collides with no other expected value in
 * either test file (not the `1` and `3` skeleton counts, not `blockHeights.length`), so no other
 * field can be satisfied by echoing it.
 *
 * WHY `5` FOR THE VARIED-GEOMETRY ROW. The same exclusions restated against that row's `6`: not `6`,
 * not `3`, not `1`, and appearing as no other expected value anywhere in the pair. It is in range
 * (`5 <= 6`) deliberately — whether an out-of-range viewport clamps, nulls, or passes through is an
 * open question with its own chartered step, and answering it by accident here would decide it in
 * silence.
 *
 * Only the two NUMBERS are shared. Each test file keeps its own geometry, its own whole-object
 * expectation and its own header: the font-gate file's two cases stay driven over ONE binding, which
 * is what kills a `derivePaginationState` that discards its argument, and nothing here dissolves
 * that. Each file also derives its `visiblePageNumber` from its own row's `currentPage` rather than
 * repeating the number, so the supplied viewport and the expected readout cannot drift apart — which
 * is the pass-through pin, now mechanical instead of a coincidence of two literals.
 */

export interface LaidOutRow {
  /** How `paginationState.crossRow.test.ts` names this row in its refutation matrix. */
  readonly name: string
  /** The "M" of "Страница N из M" — total sheets, DERIVED from that row's own geometry. */
  readonly pageCount: number
  /** The "N" — the sheet in view, PASSED THROUGH from that row's `visiblePageNumber`. */
  readonly currentPage: number
}

/** `paginationState.measuring.test.ts` — seven blocks totalling 2800px against 900px of sheet. */
export const FONT_GATE_ROW: LaidOutRow = {
  name: 'the font-gate row',
  pageCount: 4,
  currentPage: 2,
}

/** `paginationState.laidOut.test.ts` — eleven blocks totalling 3600px against 600px of sheet. */
export const VARIED_GEOMETRY_ROW: LaidOutRow = {
  name: 'the varied-geometry row',
  pageCount: 6,
  currentPage: 5,
}

export const LAID_OUT_ROWS: readonly LaidOutRow[] = [FONT_GATE_ROW, VARIED_GEOMETRY_ROW]

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
