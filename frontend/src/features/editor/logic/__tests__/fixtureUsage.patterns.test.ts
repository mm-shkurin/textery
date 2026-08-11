import { describe, expect, it } from 'vitest'
import {
  CASE_OPENER,
  EXPECTATION_OPENER,
  NAMED_VALUE,
  PINNED_ASSIGNMENT,
} from './fixtureUsage.source'

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
 * WHY THIS IS A NEW FILE AND NOT A CASE IN EITHER CONSUMER. Both are at the 200-line ceiling (174
 * and 153), and both are ABOUT the two `paginationState` test files' text; this one is about the
 * matcher itself, and its subject never moves when a pinned assertion is added or a case is
 * renamed. Filing it under either header would also put it behind an argument it does not share.
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
 * THE SECOND LEG IS A SOURCE-TEXT PIN, AND THREE PATTERNS ARE PINNED, NOT FOUR. `NAMED_VALUE`,
 * `EXPECTATION_OPENER` and `CASE_OPENER` have their `.source` compared against exact literals.
 * Probes only catch widenings someone imagined; the checksum catches ANY edit — an alternation
 * admitting a shape not listed below (`test(` openers), or a probe list quietly emptied so its own
 * case passes vacuously. `PINNED_ASSIGNMENT` and (through it) `PINNED_FIELDS` are deliberately NOT
 * pinned: `constantSites` compares `fixtureUsageIn` against a HAND-TYPED assignment list, so it
 * already moves on any change to either, and a third copy would buy no new failure mode. The three
 * pinned here are exactly the three whose every consumer leg is count-shaped or negative.
 *
 * WHAT NEITHER LEG CLAIMS. A determined widener can edit the regex, re-type the pinned `.source`
 * literal, and move the near-miss line from `rejected` to `accepted` in one commit — three edits in
 * two files, all of them reading as "this near-miss is now legal", which is the point: the motion is
 * no longer a token, and it no longer happens off screen in a module titled "mechanics only". This
 * file does not claim the patterns are CORRECT, only that they still mean what the two consumer
 * headers say they mean.
 *
 * TWO RECORDED FACTS THAT LOOK LIKE MISTAKES AND ARE NOT. `'pageCount:  4,'` (doubled space) sits in
 * the ACCEPTED list: `(.+)` swallows the extra space, the site is admitted with expression `' 4'`,
 * and `NAMED_VALUE` then rejects it — `constantSites` reports it as a CHANGED member and
 * `assignmentShape` as a re-typed value. That is the documented behaviour of both files and moving
 * it to `rejected` here would be a widening in disguise. And `'it.only(...)'` sits in CASE_OPENER's
 * REJECTED list: an `it.only` case is genuinely not counted today. That is fail-closed rather than
 * correct — the case count SHRINKS, so `assignmentShape`'s fourth case reddens — and it is pinned as
 * it stands so that admitting `.only` is a deliberate edit here rather than a side effect elsewhere.
 */

const MUST_MATCH_ASSIGNMENTS: readonly string[] = [
  'pageCount: NO_SKELETONS,',
  'railSkeletonCount: MEASURING_SURFACE.railSkeletons,',
  'pageCount:  4,',
]

const MUST_NOT_MATCH_ASSIGNMENTS: readonly string[] = [
  'pageCount: 4, // agrees with ceil',
  'pageCount : 4,',
  'pageCount: 4',
  'const pageCount: 4,',
  'totalPages: NO_SKELETONS,',
  'pageCount:',
]

const MUST_MATCH_OPENERS: readonly string[] = ['expect(state).toStrictEqual({']

const MUST_NOT_MATCH_OPENERS: readonly string[] = [
  'expect(state).toMatchObject({',
  'expect(state).toStrictEqual(EXPECTED)',
  'expect(other).toStrictEqual({',
  'expect(state).toStrictEqual({ pageCount: NO_PAGES })',
  'const expected = {',
]

const MUST_MATCH_CASES: readonly string[] = [
  "it('names a constant', () => {",
  "it.skip('measures the surface', () => {",
]

const MUST_NOT_MATCH_CASES: readonly string[] = [
  "describe('the pinned assignments', () => {",
  "it.each([1, 2])('varies', () => {",
  "it.only('names a constant', () => {",
  'itemCount(rows)',
]

const MUST_MATCH_VALUES: readonly string[] = [
  'NO_SKELETONS',
  'MEASURING_SURFACE.railSkeletons',
  'null',
]

const MUST_NOT_MATCH_VALUES: readonly string[] = [
  '4',
  '0',
  "'4'",
  '4 as number',
  'pageCount',
  'undefined',
  'NO_SKELETONS + 1',
]

interface Partition {
  readonly accepted: readonly string[]
  readonly rejected: readonly string[]
}

/**
 * The probe array is built FROM the two expected lists, so neither side of any comparison below is
 * a second spelling of the other. A pattern that changes its mind about one probe moves that probe
 * between the two halves of the received value and the named line prints in the diff.
 */
const partitionOf = (
  pattern: RegExp,
  mustMatch: readonly string[],
  mustNotMatch: readonly string[],
): Partition => {
  const probes = [...mustMatch, ...mustNotMatch]
  return {
    accepted: probes.filter((probe) => pattern.test(probe)),
    rejected: probes.filter((probe) => !pattern.test(probe)),
  }
}

describe('the source patterns, as the narrowness their consumers assume', () => {
  it('admits only `<pinned field>: <expression>,` on one trimmed line', () => {
    expect(
      partitionOf(PINNED_ASSIGNMENT, MUST_MATCH_ASSIGNMENTS, MUST_NOT_MATCH_ASSIGNMENTS),
    ).toStrictEqual({
      accepted: MUST_MATCH_ASSIGNMENTS,
      rejected: MUST_NOT_MATCH_ASSIGNMENTS,
    })
  })

  it('admits only a whole-state `toStrictEqual` opener — never the `toMatchObject` downgrade', () => {
    expect(
      partitionOf(EXPECTATION_OPENER, MUST_MATCH_OPENERS, MUST_NOT_MATCH_OPENERS),
    ).toStrictEqual({ accepted: MUST_MATCH_OPENERS, rejected: MUST_NOT_MATCH_OPENERS })
  })

  it('counts only `it(` and `it.skip(` as a case opener', () => {
    expect(partitionOf(CASE_OPENER, MUST_MATCH_CASES, MUST_NOT_MATCH_CASES)).toStrictEqual({
      accepted: MUST_MATCH_CASES,
      rejected: MUST_NOT_MATCH_CASES,
    })
  })

  it('admits only a named constant, a field of one, or `null` — never a bare number', () => {
    expect(partitionOf(NAMED_VALUE, MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES)).toStrictEqual({
      accepted: MUST_MATCH_VALUES,
      rejected: MUST_NOT_MATCH_VALUES,
    })
  })

  it('pins the source text of the three patterns no consumer list covers', () => {
    expect({
      namedValue: NAMED_VALUE.source,
      expectationOpener: EXPECTATION_OPENER.source,
      caseOpener: CASE_OPENER.source,
    }).toStrictEqual({
      namedValue: '^(?:[A-Z][A-Z0-9_]*(?:\\.[a-z][A-Za-z0-9]*)?|null)$',
      expectationOpener: '^expect\\(state\\)\\.toStrictEqual\\(\\{$',
      caseOpener: '^it(?:\\.skip)?\\(',
    })
  })
})
