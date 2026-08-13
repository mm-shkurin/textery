/**
 * Story 10, UI scenario 1.1 — the ten probe lists that define what the five patterns in
 * `fixtureUsage.source.ts` are ASSERTED to mean. Five, counted off that module's exports: the
 * header of the file you are reading said "four" for as long as `FIXTURE_IMPORT` was unexported and
 * unprobed, which is how a pattern stayed outside every leg for six consecutive reviews.
 *
 * WHY THESE ARE A MODULE AND NOT LITERALS IN THE TEST. They are the SUBJECT of the membership pin
 * now carried by `fixtureUsage.probeMembership.test.ts`, split out of `fixtureUsage.patterns.test.ts`,
 * which stood at 165 with a fifth pattern to absorb and no room left to write it. An earlier revision
 * of this sentence still named `patterns.test.ts` as the pin's home, contradicting the paragraph
 * below. They are also data with a life of their own: a reader
 * adding a near-miss line is doing something different from a reader adding a case. Splitting on
 * that seam is what this file is; it is not a key lookup, and each list stays a separately named
 * export precisely so that emptying one is a visible deletion of a named thing rather than a row
 * vanishing from a table.
 *
 * WHAT GUARDS THESE, AND EXACTLY HOW FAR IT REACHES — STATED HERE BECAUSE THE LISTS LIVE HERE.
 * Emptying a `MUST_NOT_MATCH_*` array still makes its own case in `fixtureUsage.patterns.test.ts`
 * pass VACUOUSLY (`{ accepted: [], rejected: [] }` equals itself), and is not a regex edit, so
 * `fixtureUsage.patternText.test.ts` stays byte-identical through it — the vacuity is not removed,
 * it is caught by a separate leg named below. What it costs is the MEANING
 * leg, not the widening: all five patterns are whole-text pinned by `patternText`, so a widened
 * regex reddens there whatever these lists say. An earlier revision of this paragraph named
 * `PINNED_ASSIGNMENT` as the worst case "whose probe case is its only leg" — false since
 * `patternText`'s second case was written, and struck here rather than softened. All ten lists are now pinned BY MEMBER
 * against hand-typed literals in one object in `fixtureUsage.probeMembership.test.ts`: a deletion, a
 * swap or a re-ordering is a diff printing both spellings, and the failing key names the list. A
 * LENGTH pin was drafted first and rejected as a floor — swapping a member for another string keeps every
 * length, and for the probe it drops a swap is a deletion. `MUST_MATCH_VALUES` and
 * `MUST_NOT_MATCH_VALUES` are additionally spelled out member by member on BOTH hand-typed sides of
 * the split control in `fixtureUsage.partitionControl.test.ts`, whose subject is different: not that
 * these lists are intact, but that the comparator reads the pattern it is handed.
 *
 * TWO RECORDED FACTS THAT LOOK LIKE MISTAKES AND ARE NOT. `'pageCount:  4,'` (doubled space) sits in
 * the ACCEPTED list: `(.+)` swallows the extra space, the site is admitted with expression `' 4'`,
 * and `NAMED_VALUE` then rejects it — `paginationState.constantSites.test.ts` reports it as a CHANGED
 * member and `paginationState.assignmentShape.test.ts` as a re-typed value. That is the documented
 * behaviour of both files, and moving it to `rejected` would be a widening in disguise. And
 * `'it.only(...)'` sits in `MUST_NOT_MATCH_CASES`: an `it.only` case is genuinely not counted today.
 * That is fail-closed rather than correct — the case count SHRINKS, so `assignmentShape`'s fourth
 * case reddens — and it is pinned as it stands so that admitting `.only` is a deliberate edit here
 * rather than a side effect elsewhere.
 */

export const MUST_MATCH_ASSIGNMENTS: readonly string[] = [
  'pageCount: NO_SKELETONS,',
  'railSkeletonCount: MEASURING_SURFACE.railSkeletons,',
  'pageCount:  4,',
]

export const MUST_NOT_MATCH_ASSIGNMENTS: readonly string[] = [
  'pageCount: 4, // agrees with ceil',
  'pageCount : 4,',
  'pageCount: 4',
  'const pageCount: 4,',
  'totalPages: NO_SKELETONS,',
  'pageCount:',
]

export const MUST_MATCH_OPENERS: readonly string[] = ['expect(state).toStrictEqual({']

export const MUST_NOT_MATCH_OPENERS: readonly string[] = [
  'expect(state).toMatchObject({',
  'expect(state).toStrictEqual(EXPECTED)',
  'expect(other).toStrictEqual({',
  'expect(state).toStrictEqual({ pageCount: NO_PAGES })',
  'const expected = {',
]

export const MUST_MATCH_CASES: readonly string[] = [
  "it('names a constant', () => {",
  "it.skip('measures the surface', () => {",
]

export const MUST_NOT_MATCH_CASES: readonly string[] = [
  "describe('the pinned assignments', () => {",
  "it.each([1, 2])('varies', () => {",
  "it.only('names a constant', () => {",
  'itemCount(rows)',
]

export const MUST_MATCH_VALUES: readonly string[] = [
  'NO_SKELETONS',
  'MEASURING_SURFACE.railSkeletons',
  'null',
]

export const MUST_NOT_MATCH_VALUES: readonly string[] = [
  '4',
  '0',
  "'4'",
  '4 as number',
  'pageCount',
  'undefined',
  'NO_SKELETONS + 1',
]

/**
 * THE PATH IS THE ONLY THING BINDING EITHER SOURCE FILE TO ITS FIXTURE, AND IT IS SPELLED NOWHERE
 * BUT INSIDE `FIXTURE_IMPORT`. `paginationState.constantSites.test.ts` pins the SPECIFIER LIST
 * `fixtureUsageIn` returns — the names inside the braces — and is byte-identical when the module
 * those names come from changes. So `'./otherRows.fixture'` below is not a decorative near-miss: it
 * is the incident. Point `paginationState.measuring.test.ts` at a copied `laidOutRows2.fixture`
 * exporting the same names with drifted numbers and every assertion line, every pinned specifier
 * list and `designNumbers`' pin of the ORIGINAL fixture all stay green, while the drift hole this
 * scenario exists to close is reopened. `'../fixtures/laidOutRows.fixture'` is the same attack by
 * relocation, and `'./LaidOutRows.fixture'` is what the one-character `'i'` widening buys.
 * `'./laidOutRows.fixture2'` pins the anchor, and the default import pins the braces.
 */
export const MUST_MATCH_IMPORTS: readonly string[] = [
  "import { LAID_OUT_ROWS } from './laidOutRows.fixture'",
  "import { LAID_OUT_ROWS, MEASURING_SURFACE } from './laidOutRows.fixture'",
]

export const MUST_NOT_MATCH_IMPORTS: readonly string[] = [
  "import { LAID_OUT_ROWS } from './otherRows.fixture'",
  "import { LAID_OUT_ROWS } from '../fixtures/laidOutRows.fixture'",
  "import { LAID_OUT_ROWS } from './laidOutRows.fixture2'",
  "import { LAID_OUT_ROWS } from './LaidOutRows.fixture'",
  "import LAID_OUT_ROWS from './laidOutRows.fixture'",
]
