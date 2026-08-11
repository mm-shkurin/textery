import { describe, expect, it } from 'vitest'
import {
  CASE_OPENER,
  EXPECTATION_OPENER,
  FIXTURE_IMPORT,
  NAMED_VALUE,
  PINNED_ASSIGNMENT,
} from './fixtureUsage.source'

/**
 * Story 10, UI scenario 1.1 — the SOURCE TEXT of ALL FIVE of `fixtureUsage.source.ts`' patterns,
 * pinned against exact hand-typed literals, split across three cases with different subjects. The
 * three whose consumer assertions are count-shaped are the first case; `PINNED_ASSIGNMENT` is the
 * second and `FIXTURE_IMPORT` the third, for the different reasons set out below.
 *
 * FIVE, RE-DERIVED. This header said "ALL FOUR" while the module held five: `FIXTURE_IMPORT` was
 * `const`, not `export const`, so it was invisible to a reader counting imports and to every leg in
 * this cluster. The count had been copied forward from a sibling header rather than read off the
 * module — the mechanism six consecutive reviews of this scenario found, each time as a header
 * claiming coverage its assertions did not hold. Count off the file, never off a neighbour.
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
 * WHY THE FIRST CASE IS THREE AND NOT FOUR. The three it pins are exactly the three whose every
 * consumer assertion is count-shaped or negative, and therefore blind to a zero-result-delta
 * widening. See `paginationState.constantSites.test.ts` and `paginationState.assignmentShape.test.ts`
 * headers for what those consumers do and do not see. `PINNED_ASSIGNMENT` is not one of them and is
 * pinned by the SECOND case, for a different reason.
 *
 * WHY THE FOURTH ARRIVED LATE, AND WHAT WAS MEASURED. `PINNED_ASSIGNMENT` was excluded here by
 * charter on the argument that `constantSites.test.ts` compares `fixtureUsageIn` against a HAND-TYPED
 * assignment list, so an edit to the pattern already reddens there. That argument is sound and
 * insufficient, and the paragraph it replaced conceded the gap in its own words: it covers changes
 * that alter the CURRENT yield, not every edit. Three widenings of `fixtureUsage.source.ts:61-62`
 * alter no current yield. Each was applied to that file during THIS review and the whole
 * `__tests__` directory run against it: every one reddened exactly ONE case — the second case below
 * — and left the other nineteen green (`1 failed | 19 passed | 3 skipped`, the three skips being the
 * red-phase `measuring`/`laidOut` cases, unrelated to these patterns). Nineteen green under each
 * mutant IS the pre-guard state, measured rather than inherited: those nineteen are precisely the
 * cases that existed before the second case was written. The three widenings:
 *
 *   the `'i'` flag — one character. It legalises `PAGECOUNT: 4,` and `Pagecount: 4,`; no member of
 *   `MUST_NOT_MATCH_ASSIGNMENTS` spells a case variant, so no probe moves side.
 *
 *   `PINNED_FIELDS + '|caretIndex'` — neither source file assigns `caretIndex` today, so the
 *   hand-typed list in `constantSites` does not lengthen and its `toStrictEqual` is unmoved.
 *
 *   `(.+),$` → `(.*),$` — the one shape it newly admits is `pageCount: ,`, which appears in neither
 *   source file and in no probe list.
 *
 * The module read as covered because a DIFFERENT one-token edit, the `'g'` flag, DOES redden the
 * pre-existing stack — a global RegExp carries `lastIndex` between `exec` calls. Measured the same
 * way in this review: `4 failed | 16 passed`, one case each in `patterns`, `constantSites`,
 * `assignmentShape` and the second case below. A reader who checks that one edit generalises from it
 * to the three above, which redden nothing but this file. So the exclusion is retired, not narrowed.
 *
 * WHY THE THIRD IS A CASE OF ITS OWN, AND WHAT ONLY IT SEES. `FIXTURE_IMPORT`'s consumer leg is the
 * hand-typed specifier list in `paginationState.constantSites.test.ts` — the names inside the braces.
 * The MODULE PATH is not in that list, is not in any other assertion in the directory, and is
 * spelled nowhere but inside the pattern literal. So the third case is not a checksum backstop over
 * a covered pattern the way the second is; for the path it is the only whole-text leg there is,
 * beside the probe case in `fixtureUsage.patterns.test.ts`. Widening the path to `'\.\/(?:.+)\.fixture'`
 * with an `'i'` flag was applied to the module and the whole `__tests__` directory run against it
 * BEFORE this case and its probe list existed: `20 passed | 3 skipped`, fully green, zero result
 * delta — which is what leaves a source file free to be re-pointed at a copied fixture with drifted
 * numbers while every assertion around it stays byte-identical. Its own subject, its own case.
 *
 * WHY A SECOND CASE AND NOT A FOURTH KEY IN THE FIRST. The two cases have different subjects and
 * should fail separately: the first says three patterns nothing else spells have not moved, the
 * second says the residue that `PINNED_ASSIGNMENT`'s consumer list and probe case together miss has
 * not moved. Folding them into one object would make one failing key report either claim.
 *
 * WHY THE EXPECTED SIDE RE-SPELLS `PINNED_FIELDS`. `PINNED_ASSIGNMENT` is built by `new RegExp`
 * interpolating `PINNED_FIELDS`, so pinning it requires typing that alternation out a second time.
 * That second spelling IS the guard and is not an obstacle to route around: building the expected
 * side from the imported `PINNED_FIELDS` would compare the module with itself and pass through every
 * one of the three widenings above. Nothing on the expected side below is imported.
 *
 * WHAT THIS LEG DOES NOT COVER, STATED SO NO READER BORROWS IT. (a) It sees the PATTERN only. A
 * probe list quietly emptied so its own case passes vacuously is not a pattern edit — this file is
 * byte-identical through it. That is guarded ELSEWHERE: the single case of
 * `fixtureUsage.probeMembership.test.ts` pins all ten lists member by member against hand-typed
 * literals.
 * An earlier draft of this header claimed the lists "are pinned by their own length assertion" while
 * no such assertion existed anywhere; the claim was struck rather than softened, and a pin stronger
 * than the one it described was then written — so the sentence above is a pointer to a real case, not
 * a restored promise. (b) It says
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

  it('pins the spelling AND the flags of `PINNED_ASSIGNMENT`, alternation typed out in full', () => {
    expect(PINNED_ASSIGNMENT).toStrictEqual(
      /^((?:pageCount|currentPage|(?:sheet|rail)SkeletonCount)): (.+),$/,
    )
  })

  it('pins the spelling AND the flags of `FIXTURE_IMPORT`, fixture path typed out in full', () => {
    expect(FIXTURE_IMPORT).toStrictEqual(/^import \{ (.+) \} from '\.\/laidOutRows\.fixture'$/)
  })
})
