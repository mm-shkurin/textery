import { describe, expect, it } from 'vitest'
import {
  LAID_OUT_ROWS,
  RULED_OUT_CURRENT_PAGE_HOPS,
  namedValuesOf,
  rowValuesOf,
  splitAnywherePageCount,
  type CurrentPageHop,
  type LaidOutRow,
} from './laidOutRows.fixture'

/**
 * Story 10, UI scenario 1.1 — the invariant the two laid-out rows hold JOINTLY.
 *
 * This file asserts nothing about `derivePaginationState`. It is a check on the FIXTURES, and it is
 * deliberately live rather than skipped: the defect it exists to close is that the cross-row kill of
 * `currentPage: pageCount - 1` was held by prose in two headers and by nothing that can fail, in
 * fixtures three other chartered steps are already queued to edit. A skipped guard would be prose
 * again. This one runs on every suite run, today, with the stub still unimplemented.
 *
 * WHAT IT PINS. `currentPage` is passed through and `pageCount` is derived, so the accidents worth
 * fearing are the arithmetic hops that read the geometry and never read the viewport at all. No
 * single row refutes them all — a single fixture makes every expected number a hop from every other
 * — so each hop is refuted by a specific row, and the matrix below names which. The `pageCount - 1`
 * line is the load-bearing one: `5` is `6 - 1`, so the varied-geometry row survives that hop, and it
 * dies solely because the font-gate row expects `2` where `4 - 1` is `3`.
 *
 * WHY A MATRIX RATHER THAN "at least one row refutes each hop". The weaker form stays green while
 * the kills migrate between rows, and migration is exactly the failure mode: retune the font-gate
 * row's `currentPage` to `3` and `pageCount - 1` becomes live implementation behaviour with no test
 * red anywhere. Pinning the refuting rows BY NAME means any such retune has to be argued in this
 * file rather than made in silence in a fixture whose own header calls itself "the FONT GATE".
 *
 * It is an exhaustive `toStrictEqual` over the whole matrix, so a hop deleted from the ruled-out
 * list fails here too — the list cannot be quietly shortened to make a retune pass.
 *
 * WHY THE SECOND CASE. The matrix alone is a literal, and a literal can be retuned in the same
 * motion as the fixture it describes: set the font-gate row's `currentPage` to `3` and
 * `pageCount - 1` is refuted by nobody, which shows up here as `'pageCount - 1': []` — a one-token
 * edit away from green, in a matrix whose own title still reads "each by a named row". So
 * non-emptiness is asserted SEPARATELY and as a property, computed rather than spelled out. The two
 * cases now have to be edited in OPPOSITE directions to hide a retune: emptying an entry satisfies
 * the matrix and fails the property, and deleting the hop to satisfy the property fails the
 * matrix's exhaustiveness. Neither edit is available on its own, and no edit of both is mechanical.
 *
 * THE SYMMETRIC HALF, and why it is here. The hops above cover derivations of `currentPage` FROM
 * `pageCount`. The mirror family — `pageCount` from something that is not the geometry —
 * (`blockHeights.length`, a skeleton constant, the row's own `currentPage`) was argued at equal
 * length in both test-file headers and refuted by nothing that could fail, because the fixture module
 * held the counts and described the geometry in prose. The geometry now lives in `LaidOutRow`, so the
 * second `describe` below can do two things the prose could only claim: derive each row's `pageCount`
 * from that row's own blocks, and check that no number a row's expectations are stated in collides
 * with any other. `railSkeletonCount: 3` against a three-block `blockHeights.length` is the same
 * collision, and it shipped in this scenario once.
 *
 * COLLISIONS ARE CHECKED IN BOTH DIRECTIONS, because both headers claim both. Within a row, the
 * numbers are checked against each other AND against the shared surface constants (`1` / `3` / `0`):
 * that is the `railSkeletonCount: 3` family. Across the rows, each row's own numbers are checked
 * against the other's — which is the claim `paginationState.laidOut.test.ts` states as "`6` is
 * reachable from no other value IN EITHER FILE, not `4`", and it is a different claim with a
 * different kill. A `derivePaginationState` that returns one row's whole state object frozen, for
 * whatever it is handed, dies only because `4`/`2` are not `6`/`5`; retune either row until one pair
 * meets the other and that mutation goes green with the same-row check still empty. The constants are
 * excluded from the cross-row half deliberately — both rows name the same `1` / `3` / `0`, so
 * including them would report every row as colliding with every other and the check would say
 * nothing. The pair is keyed BY NAME for the same reason the hop matrix is: adding a third row
 * without extending this expectation fails here rather than silently going unchecked.
 */
const rowsRefuting = (hop: CurrentPageHop): string[] =>
  LAID_OUT_ROWS.filter((row) => hop.derive(row.pageCount) !== row.currentPage).map((row) => row.name)

describe('the laid-out rows, read as a pair', () => {
  it('refutes every ruled-out derivation of currentPage from pageCount, each by a named row', () => {
    const matrix = Object.fromEntries(
      RULED_OUT_CURRENT_PAGE_HOPS.map((hop) => [hop.name, rowsRefuting(hop)]),
    )

    expect(matrix).toStrictEqual({
      pageCount: ['the font-gate row', 'the varied-geometry row'],
      'pageCount - 1': ['the font-gate row'],
      'pageCount / 2': ['the varied-geometry row'],
      '1': ['the font-gate row', 'the varied-geometry row'],
    })
  })

  it('leaves no ruled-out derivation unrefuted, whatever the matrix above happens to say', () => {
    const unrefuted = RULED_OUT_CURRENT_PAGE_HOPS.filter(
      (hop) => rowsRefuting(hop).length === 0,
    ).map((hop) => hop.name)

    expect(unrefuted).toStrictEqual([])
  })
})

const collisionsWithin = (row: LaidOutRow): string[] => {
  const named = Object.entries(namedValuesOf(row))

  return named.flatMap(([name, value], index) =>
    named
      .slice(index + 1)
      .filter(([, other]) => other === value)
      .map(([otherName]) => `${name} === ${otherName}`),
  )
}

const collisionsAcross = (left: LaidOutRow, right: LaidOutRow): string[] =>
  Object.entries(rowValuesOf(left)).flatMap(([leftName, value]) =>
    Object.entries(rowValuesOf(right))
      .filter(([, other]) => other === value)
      .map(([rightName]) => `${left.name}.${leftName} === ${right.name}.${rightName}`),
  )

const byName = <T>(read: (row: LaidOutRow) => T): Record<string, T> =>
  Object.fromEntries(LAID_OUT_ROWS.map((row) => [row.name, read(row)]))

const byRowPair = <T>(read: (left: LaidOutRow, right: LaidOutRow) => T): Record<string, T> =>
  Object.fromEntries(
    LAID_OUT_ROWS.flatMap((left, index) =>
      LAID_OUT_ROWS.slice(index + 1).map(
        (right) => [`${left.name} against ${right.name}`, read(left, right)] as const,
      ),
    ),
  )

describe('each laid-out row, read against its own geometry', () => {
  it('derives its expected pageCount from its own blockHeights, not from a number typed beside them', () => {
    expect(byName(splitAnywherePageCount)).toStrictEqual(byName((row) => row.pageCount))
  })

  it('states every expected number in a value no other expected number of that row can echo', () => {
    expect(byName(collisionsWithin)).toStrictEqual({
      'the font-gate row': [],
      'the varied-geometry row': [],
    })
  })

  it('states every expected number in a value no expected number of the OTHER row can echo', () => {
    expect(byRowPair(collisionsAcross)).toStrictEqual({
      'the font-gate row against the varied-geometry row': [],
    })
  })
})
