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
 * WHAT THIS FILE IS BLIND TO, AND WHERE THE OTHER LEG LIVES. A probe list only catches a widening
 * SOMEBODY IMAGINED and wrote down here. An alternation head admitting a shape no probe spells —
 * `CASE_OPENER` grown to `^(?:it|test)(?:\.skip)?\(` — moves no probe between the two halves and
 * every case below stays green. That gap is closed by a whole-pattern pin on the three patterns
 * whose every consumer leg is count-shaped or negative, and it lives in
 * `fixtureUsage.patternText.test.ts`, which carries its own argument for why three and not four.
 * Do not read the cases below as covering pattern TEXT; they cover pattern MEANING, one named line
 * at a time.
 *
 * WHAT NO LEG CLAIMS. A determined widener can edit the regex, re-type the pinned regex literal
 * in `fixtureUsage.patternText.test.ts`, and move the near-miss line from `rejected` to `accepted`
 * here in one commit — three edits in three files, all of them reading as "this near-miss is now
 * legal", which is the point: the motion is no longer a token, and it no longer happens off screen
 * in a module titled "mechanics only". This file does not claim the patterns are CORRECT, only that
 * they still mean what the two consumer headers say they mean.
 *
 * AND WHAT NOTHING GUARDS AT ALL. The six probe lists below are UNPINNED: emptying a
 * `MUST_NOT_MATCH_*` array makes its own case pass vacuously (`{ accepted: [], rejected: [] }`
 * equals itself), is not a regex edit so `fixtureUsage.patternText.test.ts` is byte-identical
 * through it, and is worst for `PINNED_ASSIGNMENT`, whose probe case is its only leg. A length pin
 * over the six is charter'd and NOT written — do not read either header as covering it.
 *
 * THE NEGATIVE CONTROL, AND WHY IT ASSERTS THE ERROR'S FIELDS RATHER THAN A PARTITION. All four
 * cases above route through one helper, and nothing above proves that helper CONSULTS `pattern`:
 * rewrite its body to `expect({ accepted, rejected }).toStrictEqual({ accepted, rejected })` — a
 * plausible "the filter was doing the same thing" simplification — and the whole behavioural leg
 * goes vacuous in one edit, with the sibling pattern pin blind because no regex text moved. The
 * named in the charter, a PASSING call with a matches-nothing pattern, cannot see that: the mutant's
 * body is tautological, so it is green for EVERY argument list and no passing call can redden it.
 * The control must therefore demand a FAILURE, and demand it by the error's STRUCTURED FIELDS —
 * `name`, `actual`, `expected`. A bare `toThrowError()` was tried and MEASURED INSUFFICIENT: it
 * passes on any throw, so a helper that reads `pattern`, tests ONE probe and short-circuits
 * satisfies it while staying tautological for the four real cases — green under the bare form, red
 * under this one. Pinning `actual` to what `/^never$/` actually yields (everything rejected, nothing
 * accepted) is what forces the pattern to have been applied to EVERY probe, so no degenerate consult
 * survives. The message is deliberately NOT matched: it is vitest's diff formatting, presentation
 * rather than data, and `objectContaining` ignores it and its `showDiff`/`operator` siblings for the
 * same reason. A ONE-SIDED neutralisation (`rejected: rejected` hardcoded) survives and survives ANY
 * call — the two halves are complements, so computed `accepted` matches its list exactly when
 * computed `rejected` does — but that gap is empty: one side still filtered keeps all four cases
 * fully discriminating. Only the TWO-sided neutralisation empties the leg.
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

/**
 * The probe array is built FROM the two expected lists, so neither side of the comparison is a
 * second spelling of the other. A pattern that changes its mind about one probe moves that probe
 * between the two halves of the received value and the named line prints in the diff.
 */
const expectPartition = (
  pattern: RegExp,
  accepted: readonly string[],
  rejected: readonly string[],
): void => {
  const probes = [...accepted, ...rejected]
  expect({
    accepted: probes.filter((probe) => pattern.test(probe)),
    rejected: probes.filter((probe) => !pattern.test(probe)),
  }).toStrictEqual({ accepted, rejected })
}

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

  it('fails the probe helper with the real partition when the pattern contradicts both lists', () => {
    expect(() => expectPartition(/^never$/, MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES)).toThrowError(
      expect.objectContaining({
        name: 'AssertionError',
        actual: { accepted: [], rejected: [...MUST_MATCH_VALUES, ...MUST_NOT_MATCH_VALUES] },
        expected: { accepted: MUST_MATCH_VALUES, rejected: MUST_NOT_MATCH_VALUES },
      }),
    )
  })
})
