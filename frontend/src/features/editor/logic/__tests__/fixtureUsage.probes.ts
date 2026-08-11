/**
 * Story 10, UI scenario 1.1 — the eight probe lists that define what the four patterns in
 * `fixtureUsage.source.ts` are ASSERTED to mean.
 *
 * WHY THESE ARE A MODULE AND NOT LITERALS IN THE TEST. They are the SUBJECT of the next chartered
 * step — a length pin over all eight — and `fixtureUsage.patterns.test.ts` was sitting at the
 * 200-line cap with zero room to write it. They are also data with a life of their own: a reader
 * adding a near-miss line is doing something different from a reader adding a case. Splitting on
 * that seam is what this file is; it is not a key lookup, and each list stays a separately named
 * export precisely so that emptying one is a visible deletion of a named thing rather than a row
 * vanishing from a table.
 *
 * WHAT NOTHING GUARDS AT ALL — STATED HERE BECAUSE THE LISTS LIVE HERE. These eight arrays are
 * UNPINNED. Emptying a `MUST_NOT_MATCH_*` array makes its own case in `fixtureUsage.patterns.test.ts`
 * pass VACUOUSLY (`{ accepted: [], rejected: [] }` equals itself); it is not a regex edit, so
 * `fixtureUsage.patternText.test.ts` is byte-identical through it; and it is worst for
 * `PINNED_ASSIGNMENT`, whose probe case is its only leg. The length pin over the eight is charter'd
 * and NOT written — do not read this file, or either test header, as covering it.
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
