import { describe, expect, it } from 'vitest'
import {
  caseOpenersIn,
  expectationBlocksIn,
  fieldsIn,
  LAID_OUT_FILE,
  MEASURING_FILE,
  pinnedFieldBlocksIn,
  reTypedValuesIn,
  type SourceFile,
} from './fixtureUsage.source'

/**
 * Story 10, UI scenario 1.1 — the pinned assignments read as a PROPERTY, not as a list.
 *
 * `paginationState.constantSites.test.ts` collects every pinned assignment in the two sibling test
 * files and compares the collection against a hand-typed expected object. Its case is named "states
 * every count by naming a fixture constant or a row field, never by re-typing its value" — but
 * nothing in it implements "never by re-typing". `PINNED_ASSIGNMENT` captures the right-hand side as
 * `(.+)`, so `pageCount: 4` is a fully LEGAL member of `pinnedAssignments`; the property holds only
 * because the expected list contains no literals today, and that list is editable in the same
 * motion that produced the defect.
 *
 * THE INCIDENT THIS FILE EXISTS FOR. Green phase, suite red in six places. A developer chasing the
 * diff retypes `laidOut.test.ts:80` to `pageCount: 6`. `constantSites` reddens AS DESIGNED — and
 * vitest prints the RECEIVED array, which is the shortest path back to green: paste it into the
 * expected object. Green, ships, and the case is still named after the property it just stopped
 * enforcing. Six weeks later the geometry retunes to `ceil(4200 / 600) = 7`, the readout stays
 * frozen at `6`, and "Страница 5 из 4" ships THROUGH the guard built to prevent it. The predecessor
 * header's "the correct repair is to update the expectation, having looked at what moved" is a
 * request addressed to a developer under a red suite. This is the mechanism.
 *
 * WHY IT IS INDEPENDENT OF THE PINNED LIST, WHICH IS THE WHOLE DELIVERABLE. This case names no
 * expected assignment. It re-reads both files and asserts a SHAPE over whatever it finds, so
 * `pageCount: 4` fails here whether or not it has been "repaired" into `constantSites`' expected
 * object. Measured: each of four mutants was run TWICE — with `constantSites` stale, and with its
 * expected list pasted over from the received array. Eight runs, eight failures here; under the
 * paste-repair the predecessor is green in all four.
 *
 * THE SHAPE, DERIVED FROM THE SITES RATHER THAN CHOSEN. Every right-hand side in the two files
 * today is one of three things: a SCREAMING_SNAKE constant (`NO_SKELETONS`), a named field read off
 * one (`MEASURING_SURFACE.railSkeletons`, `FONT_GATE_ROW.pageCount`), or a literal `null`. So the
 * constant half must start uppercase and the optional field half must start lowercase — a bare `4`,
 * `4 as number`, `'4'`, `pageCount`, `undefined` all fail. `null` is admitted BY NAME only: the
 * measuring phase's "no page count is displayed" is a decision with no fixture value to name, and
 * `undefined` or `0` silently replacing it is exactly the edit the predecessor listed those two
 * lines to catch. Widening this to tolerate a bare number is not a repair — it deletes the file.
 *
 * WHY THE SHAPE CASE NEEDS THREE COMPANIONS. An empty collection satisfies "no member has the wrong
 * shape", so a file with every assertion deleted would pass the first case in silence. Three earlier
 * answers were wrong. A FLOOR (`arrayContaining([any(String)])` per file) caught only TOTAL per-file
 * deletion. An EXACT count against `rightHandSidesIn(f).length` was DEAD — both lists were `.map`s
 * over one array, so their lengths were identically equal. A `firstBlockOf` pin (`fieldsIn(f)` sliced
 * to four) claimed a POSITION it could not see: the sites were matched per line with no notion of
 * which `expect` they sat in, so deleting block one's four lines slid block two's four names into the
 * slice and the case stayed green under the very mutant it was added for.
 *
 * SO THE GROUPING IS NOW REAL, AND EVERY POSITIONAL CLAIM RESTS ON IT. `pinnedFieldBlocksIn` walks
 * the source once and files each pinned field under the `expect(state).toStrictEqual({` opener it
 * follows. The second case asserts EVERY group, not the first, against the four names in order.
 * A block whose lines were deleted is a SHORT group; a line stranded after a block closed makes that
 * group LONG; a line hoisted above the first opener belongs to no group at all. Nothing is absorbed
 * by a neighbour, which is exactly what the slice could not promise. Measured: deleting block one's
 * four pinned lines while leaving its `expect` reddens the second case — the mutant that left the
 * slice green.
 *
 * THE THIRD CASE IS THE HOISTING GUARD, AND IT HAS NO HAND-TYPED SIDE. `fieldsIn` counts every
 * pinned line in the file, wherever it sits; the flattened groups count only lines inside a block.
 * Comparing the two compares two READ quantities. Incident it closes: green phase, `toStrictEqual`
 * fails on a field the developer reads as cosmetic, and under a red suite they hoist the expected
 * object to module scope or downgrade to `toMatchObject`. Every pinned line stays byte-identical and
 * `constantSites` stays green — but the block opener no longer matches, the lines fall outside every
 * group, and the two counts part company with no constant in this file to reconcile them. Measured:
 * downgrading block one to `toMatchObject` reddens this case and the fourth.
 *
 * THE FOURTH CASE, AND THE ONE MUTANT THAT REMAINS ONE TOKEN WIDE. It pins blocks against cases —
 * `caseOpenersIn` on the expected side, so both sides are read from the text — because every case in
 * both files asserts the whole state exactly once. Deleting an expectation from inside its `it`, or
 * adding an `it` that asserts nothing, fails on that leg alone. The second leg pins blocks against
 * `EXPECTED_EXPECTATION_BLOCKS` (2 and 1), and this is a STATED LIMIT rather than a closed hole:
 * deleting a whole case moves blocks and cases down TOGETHER, so the derived leg stays green and the
 * hand-typed one is repairable by flipping `2` to `1` — the paste-repair motion every paragraph above
 * is written against, surviving here. Measured, so it is not a guess: that deletion reddens only this
 * case, and the one-token flip returns all four to green. Closing it needs a case count read from a
 * source the deletion does not touch (the scenario spec), which no guard in this repo yet reads. Do
 * not delete this paragraph in place of fixing it.
 *
 * WHY A FIELD NAME MAY BE HAND-TYPED AT ALL. The dependency the paragraphs above rule out is a
 * dependency on VALUES. A field name is not one: it is fixed by `PaginationViewState`'s own member
 * names, it is spelled once more in `PINNED_FIELDS`, and it does not move when the design's numbers
 * retune. A block count is not a value either, for the same reason.
 *
 * THE LIST IS ORDERED, SO A REORDER REDDENS IT, AND THAT IS INHERITED RATHER THAN CHOSEN. Swapping
 * `pageCount` and `currentPage` inside one expectation is a pure reformat with no runtime meaning —
 * `toStrictEqual` over the state object does not care about key order — and it fails here (measured).
 * `constantSites` already reddens on that transpose and calls it the design; what is new is that
 * repairing it no longer clears the suite, so state the repair path: reorder
 * `PINNED_FIELDS_PER_EXPECTATION`, a hand-typed list of field names with no coupling to any value.
 * Its limit is that the two files share one order, so reordering ONE block would need the constant
 * split per file first.
 *
 * WHAT IT DOES NOT CLAIM (KNOWN limits, not a proof there are no others). It does not check that the
 * right-hand sides are the RIGHT constants (`designNumbers` owns the values) nor that they are in
 * the right places (`constantSites` owns membership and order). A re-typed literal that ALSO breaks
 * the recognised line shape (trailing comment, line wrap) is DROPPED by `PINNED_ASSIGNMENT` before
 * reaching here and surfaces only as a shortened list in `constantSites`. Blocks are attributed by
 * source ORDER, not by brace nesting, so a pinned line inside a nested object literal within a block
 * would be counted as that block's own.
 *
 * The right-hand side is NOT trimmed, so `pageCount:  NO_SKELETONS` (doubled space — a shape
 * `PINNED_ASSIGNMENT` does admit) reddens here on whitespace alone. Kept, not repaired:
 * `npm run format` cannot produce it, `prettier --check` rejects it, and a trim would widen the one
 * direction this file has no second guard for.
 */

const PINNED_FIELDS_PER_EXPECTATION: readonly string[] = [
  'pageCount',
  'currentPage',
  'sheetSkeletonCount',
  'railSkeletonCount',
]

const EXPECTED_EXPECTATION_BLOCKS: Readonly<Record<SourceFile, number>> = {
  [MEASURING_FILE]: 2,
  [LAID_OUT_FILE]: 1,
}

const everyBlockExpectedIn = (fileName: SourceFile): readonly (readonly string[])[] =>
  Array.from({ length: expectationBlocksIn(fileName) }, () => PINNED_FIELDS_PER_EXPECTATION)

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

  it('states all four fields, in order, inside EVERY expectation block — not just the first', () => {
    expect({
      [MEASURING_FILE]: pinnedFieldBlocksIn(MEASURING_FILE),
      [LAID_OUT_FILE]: pinnedFieldBlocksIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: everyBlockExpectedIn(MEASURING_FILE),
      [LAID_OUT_FILE]: everyBlockExpectedIn(LAID_OUT_FILE),
    })
  })

  it('keeps every pinned field INSIDE an expectation block — a hoisted one belongs to no block', () => {
    expect({
      [MEASURING_FILE]: fieldsIn(MEASURING_FILE),
      [LAID_OUT_FILE]: fieldsIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: pinnedFieldBlocksIn(MEASURING_FILE).flat(),
      [LAID_OUT_FILE]: pinnedFieldBlocksIn(LAID_OUT_FILE).flat(),
    })
  })

  it('keeps one whole-state expectation per case, and that many blocks — the count is read, not declared', () => {
    expect({
      [MEASURING_FILE]: {
        blocks: expectationBlocksIn(MEASURING_FILE),
        cases: caseOpenersIn(MEASURING_FILE),
      },
      [LAID_OUT_FILE]: {
        blocks: expectationBlocksIn(LAID_OUT_FILE),
        cases: caseOpenersIn(LAID_OUT_FILE),
      },
    }).toStrictEqual({
      [MEASURING_FILE]: {
        blocks: EXPECTED_EXPECTATION_BLOCKS[MEASURING_FILE],
        cases: expectationBlocksIn(MEASURING_FILE),
      },
      [LAID_OUT_FILE]: {
        blocks: EXPECTED_EXPECTATION_BLOCKS[LAID_OUT_FILE],
        cases: expectationBlocksIn(LAID_OUT_FILE),
      },
    })
  })
})
