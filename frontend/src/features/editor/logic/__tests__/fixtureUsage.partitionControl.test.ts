import { describe, expect, it } from 'vitest'
import { expectPartition } from './fixtureUsage.partition'
import { MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES } from './fixtureUsage.probes'

/**
 * Story 10, UI scenario 1.1 — the negative controls over `expectPartition` itself.
 *
 * WHY THIS IS ITS OWN FILE. `fixtureUsage.patterns.test.ts` is about the five patterns; this is
 * about the comparator those cases route through. The two subjects had nothing in common except a
 * `const`, and sharing a file kept that file at the 200-line ceiling for three consecutive units,
 * which is what blocked the probe-list MEMBERSHIP pin — by member, not the by-length one an earlier
 * revision of this sentence named, which was drafted and rejected as a floor. That pin now lives in
 * `fixtureUsage.probeMembership.test.ts`. The seam is the same one
 * `fixtureUsage.patternText.test.ts` was split on: one file per argument.
 *
 * WHY THE CONTROLS ASSERT THE ERROR'S FIELDS RATHER THAN A PARTITION. All five probe cases in the
 * sibling file route through one helper, and nothing over there proves that helper CONSULTS
 * `pattern`: rewrite its body to `expect({ accepted, rejected }).toStrictEqual({ accepted, rejected })`
 * — a plausible "the filter was doing the same thing" simplification — and the whole behavioural leg
 * goes vacuous in one edit, with the sibling pattern pin blind because no regex text moved. The
 * control named in the charter, a PASSING call with a matches-nothing pattern, cannot see that: the
 * mutant's body is tautological, so it is green for EVERY argument list and no passing call can
 * redden it. The control must therefore demand a FAILURE, and demand it by the error's STRUCTURED
 * FIELDS — `name`, `actual`, `expected`. A bare `toThrowError()` was tried and MEASURED
 * INSUFFICIENT: it passes on any throw, so a helper that reads `pattern`, tests ONE probe and
 * short-circuits satisfies it while staying tautological for the five real cases — green under the
 * bare form, red under this one. The message is deliberately NOT matched: it is vitest's diff
 * formatting, presentation rather than data, and `objectContaining` ignores it and its
 * `showDiff`/`operator` siblings for the same reason. Neither pin asserts `expected`: that field is
 * literally the two arguments the call passed in, reproduced by construction by every mutant
 * discussed here, and it cannot fail while the helper's signature is unchanged. Only `actual` does
 * work, and it is the only field pinned, so no later reader counts strength that is not there.
 *
 * TWO CONTROLS, AND WHAT EACH IS WORTH — MEASURED, NOT ARGUED. An earlier draft claimed the
 * `/^never$/` pin "forces the pattern to have been applied to EVERY probe, so no degenerate consult
 * survives". That was FALSE, and the counterexample is one line:
 * `const anyMatch = probes.some((p) => pattern.test(p))`, then compare
 * `anyMatch ? { accepted, rejected } : { accepted: [], rejected: probes }`. Every real pattern
 * matches one of its own must-match probes, so all five sibling cases compare an object with itself;
 * `/^never$/` matches none, so the mutant yields exactly the `actual` that pin demanded. A
 * matches-NOTHING (or -EVERYTHING) control certifies ONE BOOLEAN BIT. Hence the second control,
 * `/^null$/`, matching a strict non-empty SUBSET of one list: its `actual` is a SPLIT partition, and
 * no `some`/`every`/first-probe-only shortcut can produce a split. Two patterns pinned to two
 * DIFFERENT partitions is what forces the output to vary WITH `pattern`. They are NOT equally
 * load-bearing, and that is disclosed rather than averaged: the `some` mutant survives all five
 * probe cases, so the split pin is the only leg here that kills it, while the mutant that redeems
 * `/^never$/` — ignore `pattern`, hardcode `(p) => p === 'null'` — answers `[]` for every other
 * pattern and is ALREADY red at the sibling file's first case. That pin's margin is over the split
 * pin ALONE, not over the family; it is kept for the degenerate END — nothing accepted — that no
 * other call reaches.
 *
 * WHAT THE HAND-TYPED SIDES ARE FOR, AND EXACTLY HOW MUCH THEY COVER. BOTH sides of both pins are
 * HAND-TYPED — the `/^never$/` pin's TEN-member `rejected` array, the split pin's NINE-member one
 * and its one-member `accepted: ['null']` — so emptying or re-spelling `MUST_MATCH_VALUES` or
 * `MUST_NOT_MATCH_VALUES` reddens them MEMBER by member. The two arrays differ by exactly `'null'`,
 * which the split pin moves to its `accepted` side; an earlier revision of this sentence called both
 * arrays nine-member and then owed `'null'` to the `accepted` side alone, which the ten-member array
 * contradicts. Every one of the ten is spelled on a `rejected` side here. Deriving either side (the
 * two lists concatenated, `'null'` filtered out) keeps the anti-shortcut property — the predicate is
 * written HERE — but goes vacuous under that emptying, which is why the `/^never$/` pin's `rejected`
 * side is spelled out too rather than spread from the imports. Member-level coverage of all TEN
 * lists lives in `fixtureUsage.probeMembership.test.ts` — not in `fixtureUsage.patterns.test.ts`,
 * which an earlier revision named and which carries no such pin; that pin and these share literals
 * but not subjects — it says the lists have not moved, these say the comparator reads its
 * `pattern` — and neither is credit for the other.
 *
 * WHAT SURVIVES BOTH, STATED AS A LIMIT RATHER THAN CLAIMED CLOSED. (a) A ONE-SIDED neutralisation
 * (`rejected: rejected` hardcoded) survives ANY call — the two halves are complements, so computed
 * `accepted` matches its list exactly when computed `rejected` does — and that gap is empty: one side
 * still filtered keeps all five probe cases fully discriminating. (b) A mutant that BRANCHES ON
 * PATTERN IDENTITY (`pattern.source === '^never$' ? … : …`) satisfies any finite set of controls and
 * is closed by none of them. It is out of reach of this leg by construction, and it is also not the
 * hazard these controls are for: every mutant above is a plausible SIMPLIFICATION a reader could
 * make while believing the helper unchanged, and a source-string switch is not.
 */
describe('the probe comparator, as a function of the pattern it is given', () => {
  it('fails the probe helper with the real partition when the pattern contradicts both lists', () => {
    expect(() => expectPartition(/^never$/, MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES)).toThrowError(
      expect.objectContaining({
        name: 'AssertionError',
        actual: {
          accepted: [],
          rejected: [
            'NO_SKELETONS',
            'MEASURING_SURFACE.railSkeletons',
            'null',
            '4',
            '0',
            "'4'",
            '4 as number',
            'pageCount',
            'undefined',
            'NO_SKELETONS + 1',
          ],
        },
      }),
    )
  })

  it('fails with a SPLIT partition when the pattern matches exactly one probe of ten', () => {
    expect(() => expectPartition(/^null$/, MUST_MATCH_VALUES, MUST_NOT_MATCH_VALUES)).toThrowError(
      expect.objectContaining({
        name: 'AssertionError',
        actual: {
          accepted: ['null'],
          rejected: [
            'NO_SKELETONS',
            'MEASURING_SURFACE.railSkeletons',
            '4',
            '0',
            "'4'",
            '4 as number',
            'pageCount',
            'undefined',
            'NO_SKELETONS + 1',
          ],
        },
      }),
    )
  })
})
