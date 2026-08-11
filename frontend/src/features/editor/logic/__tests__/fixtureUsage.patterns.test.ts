import { describe, expect, it } from 'vitest'
import {
  CASE_OPENER,
  EXPECTATION_OPENER,
  NAMED_VALUE,
  PINNED_ASSIGNMENT,
} from './fixtureUsage.source'
import { expectPartition } from './fixtureUsage.partition'
import {
  MUST_MATCH_ASSIGNMENTS,
  MUST_MATCH_CASES,
  MUST_MATCH_OPENERS,
  MUST_MATCH_VALUES,
  MUST_NOT_MATCH_ASSIGNMENTS,
  MUST_NOT_MATCH_CASES,
  MUST_NOT_MATCH_OPENERS,
  MUST_NOT_MATCH_VALUES,
} from './fixtureUsage.probes'

/**
 * Story 10, UI scenario 1.1 — the four source patterns, guarded WHERE THEY LIVE.
 *
 * THE INCIDENT THIS FILE EXISTS FOR. `fixtureUsage.source.ts` had zero tests of its own. It holds
 * `PINNED_ASSIGNMENT`, `EXPECTATION_OPENER`, `CASE_OPENER` and `NAMED_VALUE`, and every consuming
 * assertion in `constantSites.test.ts` / `assignmentShape.test.ts` is NEGATIVE (`reTypedValuesIn`
 * must be `[]`) or COUNT-shaped (blocks, cases, group lengths). A negative assertion cannot see a
 * widening: admitting MORE lines adds nothing to an empty list, and admitting more of a line the
 * pattern already matched adds nothing to a count. So three of the four had a ZERO-RESULT-DELTA
 * widening — a green edit that deletes the property the consumer's case is named after:
 *
 *   `NAMED_VALUE` + `|\d+` — `reTypedValuesIn` filters out everything `NAMED_VALUE` accepts, so
 *   admitting bare numbers leaves case 1's received AND expected sides both `[]`. The re-typed
 *   literal property — `assignmentShape`'s headline deliverable, the thing its whole header narrates
 *   — dies in one token with the suite green.
 *
 *   `EXPECTATION_OPENER` + `|MatchObject` — re-admits the `toMatchObject` downgrade that
 *   `assignmentShape`'s third and fourth cases were measured against and written to kill. No block
 *   count moves, because the downgraded line matches again; cases 2, 3 and 4 all stay green.
 *
 *   `CASE_OPENER` widened past `it` / `it.skip` — case 4 pins `caseOpenersIn` against
 *   `expectationBlocksIn`; a pattern that also counts `describe(` or `it.each(` inflates the read
 *   side of that leg and, in a file where the two happen to stay balanced, changes nothing at all.
 *
 * AND THE ASYMMETRY THAT MADE THE MODULE READ AS GUARDED. Widening `PINNED_FIELDS` IS caught —
 * it lengthens `constantSites`' hand-typed expected list. One pattern of four is transitively
 * covered, and it is the one a reader checks first.
 *
 * WHAT IT ASSERTS, AND WHY BEHAVIOUR RATHER THAN A CHECKSUM. Each case takes a named list of lines
 * the pattern MUST match and a named list of near-misses it MUST NOT, concatenates them into one
 * probe array, partitions that array by the live pattern, and compares the partition with
 * `toStrictEqual` against the two lists themselves. Nothing is hand-typed twice: the expected sides
 * ARE the input lists. A widening moves a named near-miss out of `rejected` and appends it to
 * `accepted`, and the failure prints the offending line — `'pageCount: 4, // agrees with ceil'`,
 * `'expect(state).toMatchObject({'` — so the diff states the attack rather than a count. A
 * NARROWING is caught by the same comparison from the other side, which the consumers' count-shaped
 * cases do see but only after the fact.
 *
 * WHAT THIS FILE IS BLIND TO, AND WHERE THE OTHER LEGS LIVE. A probe list only catches a widening
 * SOMEBODY IMAGINED and wrote down. An alternation head admitting a shape no probe spells —
 * `CASE_OPENER` grown to `^(?:it|test)(?:\.skip)?\(` — moves no probe between the two halves and
 * every case below stays green. That gap is closed by a whole-pattern pin on the three patterns
 * whose every consumer leg is count-shaped or negative, and it lives in
 * `fixtureUsage.patternText.test.ts`, which carries its own argument for why three and not four.
 * Do not read the cases below as covering pattern TEXT; they cover pattern MEANING, one named line
 * at a time. And nothing below proves that `expectPartition` CONSULTS its pattern — a tautological
 * body is green for all four cases at once. That leg is `fixtureUsage.partitionControl.test.ts`.
 *
 * THE MEMBERSHIP PIN, AND WHY LENGTH ALONE WAS MEASURED INSUFFICIENT. The four cases above compare
 * the partition against THE SAME TWO LISTS the probes were built from, so an emptied list satisfies
 * its own case VACUOUSLY: `{ accepted: [], rejected: [] }` equals itself. That is not a regex edit, so
 * the checksum file is byte-identical through it, and it is worst for `PINNED_ASSIGNMENT`, whose
 * probe case is its only leg — deleting `'pageCount: 4, // agrees with ceil'` from
 * `MUST_NOT_MATCH_ASSIGNMENTS` re-legalises the non-greedy `(.+?),?$` widening this file was written
 * to kill, with everything green. A LENGTH pin over the eight lists was drafted for that and rejected
 * as a floor: it sees a deletion, but SWAPPING a near-miss for a different near-miss keeps every
 * length, and for whichever probe the swap drops a swap is exactly a deletion. The members are fixed
 * literals in a sibling module — nothing about them is indeterminate — so there was no value being
 * counted in place of read, and the final case pins all eight lists BY MEMBER instead. The expected
 * side is a second spelling on purpose, the same idiom as the regex literals in
 * `fixtureUsage.patternText.test.ts`: a deletion, a swap or a re-ordering is a diff that prints both
 * spellings, and the failing key names the list.
 *
 * WHAT THAT PIN DOES NOT MAKE REDUNDANT. The split control's hand-typed sides in
 * `fixtureUsage.partitionControl.test.ts` also spell out `MUST_MATCH_VALUES` and
 * `MUST_NOT_MATCH_VALUES` member by member, but they are not a duplicate of the case below: their
 * subject is that `expectPartition` CONSULTS its pattern, and the members are how they say it. Two
 * legs, one shared literal, neither one credit for the other.
 *
 * WHAT NO LEG CLAIMS. A determined widener can still do it: edit the regex, re-type the pinned regex
 * literal in `fixtureUsage.patternText.test.ts`, move the near-miss line from `rejected` to
 * `accepted` in `fixtureUsage.probes.ts`, and re-type that same line on the other side of the
 * membership pin below — four edits in three files, all of them reading as "this near-miss is now
 * legal", which is the point: the motion is no longer a token, and it no longer happens off screen in
 * a module titled "mechanics only". This file does not claim the patterns are CORRECT, only that they
 * still mean what the two consumer headers say they mean.
 */
describe('the source patterns, as the narrowness their consumers assume', () => {
  it('admits only `<pinned field>: <expression>,` on one trimmed line', () => {
    expectPartition(PINNED_ASSIGNMENT, MUST_MATCH_ASSIGNMENTS, MUST_NOT_MATCH_ASSIGNMENTS)
  })

  it('admits only a whole-state `toStrictEqual` opener — never the `toMatchObject` downgrade', () => {
    expectPartition(EXPECTATION_OPENER, MUST_MATCH_OPENERS, MUST_NOT_MATCH_OPENERS)
  })

  it('counts only `it(` and `it.skip(` as a case opener', () => {
    expectPartition(CASE_OPENER, MUST_MATCH_CASES, MUST_NOT_MATCH_CASES)
  })

  it('admits only a named constant, a field of one, or `null` — never a bare number', () => {
    expectPartition(NAMED_VALUE, MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES)
  })

  it('pins every member of all eight probe lists, so no case above can be emptied or re-spelled', () => {
    expect({
      mustMatchAssignments: MUST_MATCH_ASSIGNMENTS,
      mustNotMatchAssignments: MUST_NOT_MATCH_ASSIGNMENTS,
      mustMatchOpeners: MUST_MATCH_OPENERS,
      mustNotMatchOpeners: MUST_NOT_MATCH_OPENERS,
      mustMatchCases: MUST_MATCH_CASES,
      mustNotMatchCases: MUST_NOT_MATCH_CASES,
      mustMatchValues: MUST_MATCH_VALUES,
      mustNotMatchValues: MUST_NOT_MATCH_VALUES,
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
    })
  })
})
