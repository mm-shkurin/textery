import { describe, expect, it } from 'vitest'
import { CASE_OPENER, EXPECTATION_OPENER, NAMED_VALUE } from './fixtureUsage.source'

/**
 * Story 10, UI scenario 1.1 — the SOURCE TEXT of three of `fixtureUsage.source.ts`' four patterns,
 * pinned against exact literals.
 *
 * WHAT THIS BACKSTOPS THAT A PROBE LIST CANNOT. `fixtureUsage.patterns.test.ts` partitions a named
 * list of must-match lines and a named list of near-misses by each live pattern. That is a strong
 * leg and a blind one in exactly one direction: it can only see a widening SOMEBODY IMAGINED and
 * wrote down. An alternation head admitting a shape no probe spells — `CASE_OPENER` grown to
 * `^(?:it|test)(?:\.skip)?\(`, surfaced by `/test-review` — moves no probe between the two halves,
 * because no probe is a `test(` opener. Every probe stays on the side it was on and that file is
 * green. A checksum has no such gap: it moves on ANY edit to the pattern text, imagined or not, and
 * the diff prints the two spellings side by side so the reader sees precisely what was admitted.
 * That is the whole trade — the probes say what the patterns MEAN, this says they have not moved.
 *
 * WHY THREE AND NOT FOUR. `PINNED_ASSIGNMENT` is not pinned here. `constantSites.test.ts` compares
 * `fixtureUsageIn` against a HAND-TYPED assignment list, so an edit that changes what the current
 * source lines yield already reddens there — a second copy of the same claim would buy no new
 * failure mode. That rationale is narrower than it sounds and is charter'd for repair separately:
 * it covers changes that alter the CURRENT yield, not every edit, so `PINNED_ASSIGNMENT`'s probe
 * case is effectively its only leg. The three pinned here are exactly the three whose every
 * consumer assertion is count-shaped or negative, and therefore blind to a zero-result-delta
 * widening. See `paginationState.constantSites.test.ts` and `paginationState.assignmentShape.ts`
 * headers for what those consumers do and do not see.
 *
 * WHAT THIS LEG DOES NOT COVER, STATED SO NO READER BORROWS IT. (a) It sees the PATTERN only. A
 * probe list quietly emptied so its own case passes vacuously is not a pattern edit — this file is
 * byte-identical through it. **Nothing guards that today.** An earlier draft of this header claimed
 * the lists "are pinned by their own length assertion"; no such assertion exists anywhere in
 * `__tests__`, and the length pin is charter'd and unwritten. The claim is struck rather than
 * softened, because a reader who trusts it closes the chartered step as already done. (b) It says
 * nothing about whether the patterns are CORRECT — only that changing one is a deliberate edit to a
 * literal that reads as a spelling, in a file whose only subject is that spelling.
 *
 * WHY WHOLE REGEXES AND NOT `.source`. `.source` EXCLUDES FLAGS, so a `.source` pin agrees with
 * `/^it(?:\.skip)?\(/g`. `toStrictEqual` on the RegExp objects themselves compares source AND flags
 * in the same call, so the flag gap is closed here rather than traced-and-excused, and the expected
 * side stops being a double-escaped string that no reader can diff against the real literal.
 */
describe('the pattern source text, as the spelling its consumers were measured against', () => {
  it('pins the spelling AND the flags of the three patterns no consumer list covers', () => {
    expect({
      namedValue: NAMED_VALUE,
      expectationOpener: EXPECTATION_OPENER,
      caseOpener: CASE_OPENER,
    }).toStrictEqual({
      namedValue: /^(?:[A-Z][A-Z0-9_]*(?:\.[a-z][A-Za-z0-9]*)?|null)$/,
      expectationOpener: /^expect\(state\)\.toStrictEqual\(\{$/,
      caseOpener: /^it(?:\.skip)?\(/,
    })
  })
})
