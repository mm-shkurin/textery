import { describe, expect, it } from 'vitest'
import {
  MUST_MATCH_ASSIGNMENTS,
  MUST_MATCH_CASES,
  MUST_MATCH_IMPORTS,
  MUST_MATCH_OPENERS,
  MUST_MATCH_VALUES,
  MUST_NOT_MATCH_ASSIGNMENTS,
  MUST_NOT_MATCH_CASES,
  MUST_NOT_MATCH_IMPORTS,
  MUST_NOT_MATCH_OPENERS,
  MUST_NOT_MATCH_VALUES,
} from './fixtureUsage.probes'

/**
 * Story 10, UI scenario 1.1 — the TEN probe lists of `fixtureUsage.probes.ts`, pinned member by
 * member against hand-typed literals. Ten is counted off the exports of that module, not carried
 * over from a sibling header: five patterns, a must-match and a must-not-match list each.
 *
 * WHY IT IS A FILE OF ITS OWN. It was the last case of `fixtureUsage.patterns.test.ts` until this
 * unit. That file's other cases state what the patterns MEAN, one named line at a time; this one
 * states that the lists those cases are built from are still the lists that were reviewed. Two
 * subjects, and the sibling's own header is the argument for splitting rather than folding — it
 * refuses to put two claims behind one failing key. The mechanical trigger was the 200-line cap:
 * `patterns.test.ts` stood at 165 with a fifth pattern to absorb, and the membership pin is the
 * one part of it that reads on its own.
 *
 * WHAT IT CATCHES THAT THE PROBE CASES CANNOT. Each probe case compares a partition against THE
 * SAME TWO LISTS its probes were built from, so an EMPTIED list satisfies its own case VACUOUSLY:
 * `{ accepted: [], rejected: [] }` equals itself. Emptying a list is not a regex edit, so
 * `fixtureUsage.patternText.test.ts` is byte-identical through it.
 *
 * WHAT IT DOES NOT CATCH, SO THE CLAIM ABOVE IS NOT BORROWED TOO WIDELY. It does not stand between
 * a widening and a green suite. All five patterns are whole-text pinned by `patternText`, so
 * deleting `'pageCount: 4, // agrees with ceil'` from `MUST_NOT_MATCH_ASSIGNMENTS` does NOT
 * re-legalise the non-greedy `(.+?),?$` widening, and deleting
 * `"import { LAID_OUT_ROWS } from './otherRows.fixture'"` from `MUST_NOT_MATCH_IMPORTS` does NOT
 * re-legalise pointing a source file at a COPIED fixture — `patternText`'s second and third cases
 * redden on either edit. The first draft of this paragraph asserted both re-legalisations and named
 * "the lists whose probe case is their pattern's only behavioural leg", a set that is EMPTY; the
 * claim was struck by review rather than softened. What an emptied list actually costs is the
 * MEANING leg: `patterns.test.ts` keeps saying the pattern is narrow while having stopped testing
 * it, and the spelling pin cannot tell a correct regex from a wrong one it was handed. That is the
 * gap this file closes, and it is smaller than the struck sentence claimed.
 *
 * WHY BY MEMBER AND NOT BY LENGTH. A length pin was drafted for this and rejected as a floor: it
 * sees a deletion, but SWAPPING a near-miss for a different near-miss keeps every length, and for
 * whichever probe the swap drops a swap is exactly a deletion. The members are fixed literals in a
 * sibling module — nothing about them is indeterminate — so there is no value being counted in place
 * of read. The expected side is a second spelling on purpose, the same idiom as the regex literals
 * in `fixtureUsage.patternText.test.ts`: a deletion, a swap or a re-ordering is a diff that prints
 * both spellings, and the failing key names the list. Nothing below is imported onto the expected
 * side; deriving it would compare the module with itself and pass through every deletion.
 *
 * WHAT THIS DOES NOT MAKE REDUNDANT. `fixtureUsage.partitionControl.test.ts` also spells out
 * `MUST_MATCH_VALUES` and `MUST_NOT_MATCH_VALUES` member by member on both hand-typed sides. Its
 * subject is different — that `expectPartition` CONSULTS the pattern it is handed — and the members
 * are how it says it. Two legs, one shared literal, neither one credit for the other.
 */
describe('the probe lists, as the membership their cases were reviewed against', () => {
  it('pins every member of all ten probe lists, so no probe case can be emptied or re-spelled', () => {
    expect({
      mustMatchAssignments: MUST_MATCH_ASSIGNMENTS,
      mustNotMatchAssignments: MUST_NOT_MATCH_ASSIGNMENTS,
      mustMatchOpeners: MUST_MATCH_OPENERS,
      mustNotMatchOpeners: MUST_NOT_MATCH_OPENERS,
      mustMatchCases: MUST_MATCH_CASES,
      mustNotMatchCases: MUST_NOT_MATCH_CASES,
      mustMatchValues: MUST_MATCH_VALUES,
      mustNotMatchValues: MUST_NOT_MATCH_VALUES,
      mustMatchImports: MUST_MATCH_IMPORTS,
      mustNotMatchImports: MUST_NOT_MATCH_IMPORTS,
    }).toStrictEqual({
      mustMatchAssignments: [
        'pageCount: NO_SKELETONS,',
        'railSkeletonCount: MEASURING_SURFACE.railSkeletons,',
        'pageCount:  4,',
      ],
      mustNotMatchAssignments: [
        'pageCount: 4, // agrees with ceil',
        'pageCount : 4,',
        'pageCount: 4',
        'const pageCount: 4,',
        'totalPages: NO_SKELETONS,',
        'pageCount:',
      ],
      mustMatchOpeners: ['expect(state).toStrictEqual({'],
      mustNotMatchOpeners: [
        'expect(state).toMatchObject({',
        'expect(state).toStrictEqual(EXPECTED)',
        'expect(other).toStrictEqual({',
        'expect(state).toStrictEqual({ pageCount: NO_PAGES })',
        'const expected = {',
      ],
      mustMatchCases: ["it('names a constant', () => {", "it.skip('measures the surface', () => {"],
      mustNotMatchCases: [
        "describe('the pinned assignments', () => {",
        "it.each([1, 2])('varies', () => {",
        "it.only('names a constant', () => {",
        'itemCount(rows)',
      ],
      mustMatchValues: ['NO_SKELETONS', 'MEASURING_SURFACE.railSkeletons', 'null'],
      mustNotMatchValues: [
        '4',
        '0',
        "'4'",
        '4 as number',
        'pageCount',
        'undefined',
        'NO_SKELETONS + 1',
      ],
      mustMatchImports: [
        "import { LAID_OUT_ROWS } from './laidOutRows.fixture'",
        "import { LAID_OUT_ROWS, MEASURING_SURFACE } from './laidOutRows.fixture'",
      ],
      mustNotMatchImports: [
        "import { LAID_OUT_ROWS } from './otherRows.fixture'",
        "import { LAID_OUT_ROWS } from '../fixtures/laidOutRows.fixture'",
        "import { LAID_OUT_ROWS } from './laidOutRows.fixture2'",
        "import { LAID_OUT_ROWS } from './LaidOutRows.fixture'",
        "import LAID_OUT_ROWS from './laidOutRows.fixture'",
      ],
    })
  })
})
