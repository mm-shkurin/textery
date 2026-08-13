import { describe, it } from 'vitest'
import {
  CASE_OPENER,
  EXPECTATION_OPENER,
  FIXTURE_IMPORT,
  NAMED_VALUE,
  PINNED_ASSIGNMENT,
} from './fixtureUsage.source'
import { expectPartition } from './fixtureUsage.partition'
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
 * Story 10, UI scenario 1.1 — the FIVE source patterns, guarded WHERE THEY LIVE. Five is counted
 * off the exports of `fixtureUsage.source.ts` rather than copied from this header's own previous
 * revision, which said four: `FIXTURE_IMPORT` was `const`, not `export const`, and every count in
 * this cluster of files had been carried forward from a sibling instead of re-derived, so the one
 * pattern nobody counted was the one pattern nobody probed. See the last section below for what
 * that cost and what closes it.
 *
 * THE INCIDENT THIS FILE EXISTS FOR. `fixtureUsage.source.ts` had zero tests of its own. The four a
 * reader could then count were `PINNED_ASSIGNMENT`, `EXPECTATION_OPENER`, `CASE_OPENER` and
 * `NAMED_VALUE` — `FIXTURE_IMPORT` was the unexported fifth, which is the defect above — and every
 * consuming assertion in `constantSites.test.ts` / `assignmentShape.test.ts` is NEGATIVE (`reTypedValuesIn`
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
 * it lengthens `constantSites`' hand-typed expected list. One pattern of the four then counted was
 * transitively covered, and it is the one a reader checks first.
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
 * every case below stays green. That gap is closed by a whole-pattern pin, and it lives in
 * `fixtureUsage.patternText.test.ts`, which now pins ALL FIVE across three cases with a separate
 * argument for each: the three whose every consumer leg is count-shaped or negative are its first
 * case, `PINNED_ASSIGNMENT` its second, `FIXTURE_IMPORT` its third. An earlier revision of this
 * paragraph said "the three patterns", from before the second and third cases retired that
 * exclusion. Do not read the cases below as covering pattern TEXT; they cover pattern MEANING, one
 * named line at a time. And nothing below proves that `expectPartition` CONSULTS its pattern — a
 * tautological body is green for all five cases at once. That leg is
 * `fixtureUsage.partitionControl.test.ts`.
 *
 * THE VACUITY THIS FILE NO LONGER CARRIES, AND WHERE IT WENT. Every case below compares the
 * partition against THE SAME TWO LISTS its probes were built from, so an emptied list satisfies its
 * own case VACUOUSLY: `{ accepted: [], rejected: [] }` equals itself. The member-by-member pin over
 * all ten lists that closes this was the last case of this file until the fifth pattern arrived and
 * the 200-line cap forced a choice; it now lives in `fixtureUsage.probeMembership.test.ts`, which
 * carries the argument for by-member over by-length and for a hand-typed expected side. The seam is
 * the subject: below is what the patterns MEAN, there is that the lists saying so are intact.
 *
 * THE FIFTH PATTERN, AND WHY ITS PROBE LIST IS THE LOAD-BEARING ONE. `FIXTURE_IMPORT` matches the
 * fixture import line of each source file and yields the SPECIFIERS inside the braces.
 * `paginationState.constantSites.test.ts` pins those specifiers against a hand-typed list — and is
 * byte-identical when the MODULE they come from changes, because the path is spelled nowhere but
 * inside the pattern. Point `paginationState.measuring.test.ts` at a copied `laidOutRows2.fixture`
 * exporting the same names with drifted numbers and the whole suite stays green. The case below and
 * the third case of `fixtureUsage.patternText.test.ts` are the only two assertions in the directory
 * that read the path AS THE PATTERN'S — one by behaviour, one by spelling; no consumer reads it.
 * The qualifier is load-bearing and was added by review: `fixtureUsage.probeMembership.test.ts`
 * hand-types that same path six times on its expected side, but as the text of a PROBE, so it is
 * unmoved by any edit to the pattern. Counting it would have been the third header in this cluster
 * to claim a coverage its assertions do not hold.
 *
 * WHAT NO LEG CLAIMS. A determined widener can still do it: edit the regex, re-type the pinned regex
 * literal in `fixtureUsage.patternText.test.ts`, move the near-miss line from `rejected` to
 * `accepted` in `fixtureUsage.probes.ts`, and re-type that same line on the other side of the
 * membership pin — four edits in four files, all of them reading as "this near-miss is now
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

  it("admits only a './laidOutRows.fixture' import — never another path, casing or default", () => {
    expectPartition(FIXTURE_IMPORT, MUST_MATCH_IMPORTS, MUST_NOT_MATCH_IMPORTS)
  })
})
