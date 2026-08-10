import { describe, expect, it } from 'vitest'
import { fixtureUsageIn, LAID_OUT_FILE, MEASURING_FILE } from './fixtureUsage.source'

/**
 * Story 10, UI scenario 1.1 — the pinned assignments read as a PROPERTY, not as a list.
 *
 * `paginationState.constantSites.test.ts` collects every pinned assignment in the two sibling test
 * files and compares the collection against a hand-typed expected object. That case is named
 * "states every count by naming a fixture constant or a row field, never by re-typing its value" —
 * but nothing in it implements "never by re-typing". `PINNED_ASSIGNMENT` captures the right-hand
 * side as `(.+)`, so `pageCount: 4` is a fully LEGAL member of `pinnedAssignments`; the property
 * holds only because the expected list happens to contain no literals today, and that list is
 * editable in the same motion that produced the defect.
 *
 * THE INCIDENT THIS FILE EXISTS FOR. Green phase, suite red in six places. A developer chasing the
 * diff retypes `laidOut.test.ts:80` to `pageCount: 6`. `constantSites` reddens AS DESIGNED — and
 * vitest prints the RECEIVED array, which is the shortest path back to green: paste it into the
 * expected object. Green, ships, and the case is still named after the property it just stopped
 * enforcing. Six weeks later the geometry retunes to `ceil(4200 / 600) = 7`, the readout stays
 * frozen at `6`, and "Страница 5 из 4" ships THROUGH the guard built to prevent it. The predecessor
 * header's defence — "the correct repair is to update the expectation, having looked at what
 * moved" — is a request addressed to a developer under a red suite. This is the mechanism.
 *
 * WHY IT IS INDEPENDENT OF THE PINNED LIST, WHICH IS THE WHOLE DELIVERABLE. This case names no
 * expected assignment and no expected count. It re-reads both files through the same
 * `fixtureUsageIn` and asserts a SHAPE over whatever it finds, so `pageCount: 4` fails here whether
 * or not it has been "repaired" into `constantSites`' expected object. Measured, not argued: each
 * of the four mutants below was run TWICE — once with `constantSites` stale (two cases red) and once
 * with its expected list pasted over from the received array (this case red, alone). Eight runs,
 * eight failures; under the paste-repair the predecessor is green in all four.
 *
 * THE SHAPE, DERIVED FROM THE SITES RATHER THAN CHOSEN. Every right-hand side in the two files
 * today is one of three things: a SCREAMING_SNAKE constant (`NO_SKELETONS`), a named field read off
 * one (`MEASURING_SURFACE.railSkeletons`, `FONT_GATE_ROW.pageCount`,
 * `VARIED_GEOMETRY_ROW.currentPage`), or a literal `null`. So the constant half must start
 * uppercase and the optional field half must start lowercase — a bare `4`, `4 as number`, `'4'`,
 * `pageCount`, and `undefined` all fail. `null` is admitted BY NAME and nothing else is: the
 * measuring phase's "no page count is displayed" is a decision with no fixture value to name, and
 * `undefined` or `0` silently replacing it is exactly the edit the predecessor listed those two
 * lines to catch. Widening this to tolerate a bare number is not a repair — it deletes the file.
 *
 * WHY THE SECOND CASE PINS THE FIRST BLOCK, AND TWO CORRECTIONS TO WHAT USED TO STAND HERE. An
 * empty collection satisfies "no member has the wrong shape", so a file with every assertion
 * deleted would pass the first case in silence. This paragraph has now answered that twice, wrongly
 * in opposite directions. It first used a FLOOR — `arrayContaining([any(String)])` per file — loose,
 * and catching only TOTAL per-file deletion. It then replaced the floor with an EXACT count,
 * `rightHandSidesIn(f).length` against `pinnedFieldsExpectedIn(f).length`, on the argument that the
 * floor's stated reason ("pinning the number would re-import the hand-typed dependency") had been
 * made false by the third case hand-typing the multiplicity anyway. That argument about the REASON
 * is correct and stands. The replacement it licensed was not. Two things were wrong with it.
 *
 * It was DEAD. Both lists are `.map`s over the same `pinnedAssignments` array, so their lengths are
 * identically equal, and the third case's ordered `toStrictEqual` already implies that equality —
 * the count could not fail in any run where the third case passed. And it moved this file's LAST
 * claim that did not read `EXPECTATION_BLOCKS` onto that constant. Measured, not argued: deleting
 * all four pinned lines from `laidOut.test.ts` and setting its entry to `0` left ALL THREE cases
 * GREEN — the file vacuous over that whole file, bought with a two-token edit inside this one,
 * which is the paste-repair motion every paragraph above is written against. The floor, for all its
 * looseness, was red under exactly that mutant.
 *
 * So the second case now pins the FIRST expectation block of each file: `fieldsIn(f)` truncated to
 * `PINNED_FIELDS_PER_EXPECTATION.length`, against those four names. It is STRICT (it names the
 * fields and prints which one left which file, which the floor never could), non-vacuous (an
 * emptied file yields `[]` against four names), and it reads NO block count — so zeroing
 * `EXPECTATION_BLOCKS` reddens it while the third case goes quiet. It is redundant with the third
 * case whenever that constant is honest; that redundancy IS the guard, and it is why no floor is
 * needed to buy it. The dependency the original paragraph feared is a dependency on VALUES; a block
 * count is not a value, for the same reason a field name is not (see two paragraphs down).
 *
 * A FLOOR WOULD NOT HAVE CLOSED DELETION EITHER, WHICH IS WHY THE THIRD CASE EXISTS. A floor of one
 * closes TOTAL per-file deletion only: delete ONE line and it is still satisfied by the three that
 * remain. That is the whole of the next incident, and it is the same paste-repair one move on.
 * Green phase,
 * `derivePaginationState` emits a laid-out state with no `currentPage`; re-typing `currentPage: 5` at
 * `laidOut.test.ts:81` is now closed by the shape case, so the next-shortest path back to green is to
 * DELETE the line and paste the received array over `constantSites`' expected object. `constantSites`
 * is green (its list is whatever vitest printed), the shape case is green (nothing re-typed among what
 * REMAINS, and the file still contributes three sites), and "Страница 5 из 6" renders "Страница 1 из
 * 6" forever with both guards green. `WHAT IT DOES NOT CLAIM` below hands membership to
 * `constantSites` — which is precisely the guard whose repair path this file exists because it does
 * not trust, so membership could not be left there alone.
 *
 * THE THIRD CASE PINS THE FIELD SET, WHICH IS THE HALF THAT CAN BE HAND-TYPED WITHOUT THE DEPENDENCY.
 * `PINNED_ASSIGNMENT` already captures the field separately from the value; this case reads that half
 * and compares each file's ORDERED field list against a hand-typed one. The reason this does not
 * re-import the dependency the two paragraphs above rule out is that a FIELD NAME is not a value: it
 * is fixed by `PaginationViewState`'s own member names, it is already spelled twice in this repo
 * (`PINNED_ASSIGNMENT` and `PINNED_FIELD`), and it does not move when the design's numbers retune.
 * The list is `pageCount, currentPage, sheetSkeletonCount, railSkeletonCount` — measuring TWICE
 * (it has two expectation blocks, `:97-100` and `:184-187`), laid-out ONCE (`:80-83`). The
 * multiplicity is the load-bearing part: a per-file SET would be satisfied by the second block alone
 * after the first is deleted wholesale, so the repeats are written out. When it fails it prints which
 * field left which file, which is what a floor of one could never say.
 *
 * THE LIST IS ORDERED, SO A REORDER REDDENS IT, AND THAT IS INHERITED RATHER THAN CHOSEN. Swapping
 * `pageCount` and `currentPage` inside one expectation is a pure reformat with no runtime meaning —
 * `toStrictEqual` over the state object does not care about key order — and it fails here (verified,
 * in both directions: red with `constantSites` stale AND with its expected list repaired). This is
 * not a new brittleness: `constantSites` already reddens on exactly that transpose and its header
 * already calls it the design. What IS new is that repairing `constantSites` no longer clears the
 * suite, so the repair path must be stated. The repair for a genuine reorder is to reorder
 * `PINNED_FIELDS_PER_EXPECTATION` — a hand-typed list of field names, with no coupling to any value.
 * Its limit is that the two files share one order: reordering ONE block would need the constant
 * split per file first, and reordering one block alone is not an edit anyone has had cause to make.
 *
 * WHAT IT DOES NOT CLAIM. It does not check that the right-hand sides are the RIGHT constants
 * (`designNumbers` owns the values) nor that they are in the right places (`constantSites` owns
 * membership and order) — the two cases are complements and neither subsumes the other. In
 * particular a re-typed literal that ALSO breaks the recognised line shape (a trailing comment, a
 * line wrap) is DROPPED by `PINNED_ASSIGNMENT` before reaching here, and surfaces only as a
 * shortened list in `constantSites`. This case sees a mutation only where the site still looks like
 * an assignment; that is the common case and the one the paste-repair reaches.
 *
 * The right-hand side is NOT trimmed after the field prefix is stripped, so `pageCount:  NO_SKELETONS`
 * (doubled space — a shape `PINNED_ASSIGNMENT` does admit) reddens here on whitespace alone. That is
 * kept rather than repaired: `npm run format` cannot produce it, `prettier --check` rejects it, and a
 * trim would be a widening in the one direction this file has no second guard for.
 */

const PINNED_FIELD = /^(?:pageCount|currentPage|(?:sheet|rail)SkeletonCount): /
const NAMED_VALUE = /^(?:[A-Z][A-Z0-9_]*(?:\.[a-z][A-Za-z0-9]*)?|null)$/

const rightHandSidesIn = (fileName: string): readonly string[] =>
  fixtureUsageIn(fileName).pinnedAssignments.map((assignment) =>
    assignment.replace(PINNED_FIELD, ''),
  )

const fieldsIn = (fileName: string): readonly string[] =>
  fixtureUsageIn(fileName).pinnedAssignments.map((assignment) =>
    assignment.slice(0, assignment.indexOf(':')),
  )

const PINNED_FIELDS_PER_EXPECTATION: readonly string[] = [
  'pageCount',
  'currentPage',
  'sheetSkeletonCount',
  'railSkeletonCount',
]

const firstBlockOf = (fileName: string): readonly string[] =>
  fieldsIn(fileName).slice(0, PINNED_FIELDS_PER_EXPECTATION.length)

const EXPECTATION_BLOCKS: Readonly<Record<string, number>> = {
  [MEASURING_FILE]: 2,
  [LAID_OUT_FILE]: 1,
}

const pinnedFieldsExpectedIn = (fileName: string): readonly string[] =>
  Array.from({ length: EXPECTATION_BLOCKS[fileName] }, () => PINNED_FIELDS_PER_EXPECTATION).flat()

const reTypedValuesIn = (fileName: string): readonly string[] =>
  rightHandSidesIn(fileName).filter((expression) => !NAMED_VALUE.test(expression))

describe('the pinned assignments, as a property rather than as a list', () => {
  it('names a constant, a field of one, or null — never a re-typed value', () => {
    expect({
      [MEASURING_FILE]: reTypedValuesIn(MEASURING_FILE),
      [LAID_OUT_FILE]: reTypedValuesIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: [],
      [LAID_OUT_FILE]: [],
    })
  })

  it('opens each file with a whole expectation block — the one claim here that reads no block count', () => {
    expect({
      [MEASURING_FILE]: firstBlockOf(MEASURING_FILE),
      [LAID_OUT_FILE]: firstBlockOf(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: PINNED_FIELDS_PER_EXPECTATION,
      [LAID_OUT_FILE]: PINNED_FIELDS_PER_EXPECTATION,
    })
  })

  it('still contributes every pinned field from every expectation block — a dropped assertion is not a shorter list', () => {
    expect({
      [MEASURING_FILE]: fieldsIn(MEASURING_FILE),
      [LAID_OUT_FILE]: fieldsIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: pinnedFieldsExpectedIn(MEASURING_FILE),
      [LAID_OUT_FILE]: pinnedFieldsExpectedIn(LAID_OUT_FILE),
    })
  })
})
