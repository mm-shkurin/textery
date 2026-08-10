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
 * WHY A NON-VACUITY FLOOR AND NOT A PINNED COUNT. An empty collection satisfies "no member has the
 * wrong shape", so deleting every assertion in both files would pass this case in silence. Each
 * file is therefore required to contribute at least one site. It is a floor, not a count: pinning
 * the exact number would re-import the dependency on a hand-typed expectation that this file exists
 * to be free of, and the exact-membership job is `constantSites`'. The floor is stated over the
 * COLLECTED LISTS rather than over `length > 0`: an `arrayContaining([any(String)])` is unsatisfiable
 * by an empty list exactly as the boolean was, but when it fails vitest prints the sites it actually
 * found in each file, which is the first thing a reader of this failure needs. A boolean says only
 * `false`, and a floor that reads `false` is indistinguishable from a floor read off the wrong file.
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

  it('has sites in both files to say that about', () => {
    expect({
      [MEASURING_FILE]: rightHandSidesIn(MEASURING_FILE),
      [LAID_OUT_FILE]: rightHandSidesIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: expect.arrayContaining([expect.any(String)]),
      [LAID_OUT_FILE]: expect.arrayContaining([expect.any(String)]),
    })
  })
})
