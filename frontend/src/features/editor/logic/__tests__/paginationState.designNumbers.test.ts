import { describe, expect, it } from 'vitest'
import { MEASURING_SURFACE, NO_SKELETONS } from './laidOutRows.fixture'

/**
 * Story 10, UI scenario 1.1 — THE ONE PLACE THE MEASURING SURFACE'S DESIGN NUMBERS ARE DECIDED.
 *
 * `MEASURING_SURFACE.sheetSkeletons` is `1`, `MEASURING_SURFACE.railSkeletons` is `3`, and
 * `NO_SKELETONS` is `0`. Those three values are what `paginationState.measuring.test.ts:99-100,186-187`
 * and `paginationState.laidOut.test.ts:82-83` expect, read by name so the four assertions and the
 * collision check share ONE declaration. That sharing is deliberate and is not being undone here.
 *
 * A LEGITIMATE DESIGN CHANGE IS EDITED HERE, ON PURPOSE. Grow the rail to four rows, or change how
 * many skeleton sheets the measuring surface shows, and the correct motion is: change the constant in
 * `laidOutRows.fixture.ts`, then change the literal below to match, in the same commit, having looked
 * at the mockup. The redness this case produces in between is the guard working. It is NOT a false
 * positive, and it is not repaired by deleting the case.
 *
 * WHY THIS EXISTS AT ALL. Making the fixture the single declaration closed a DRIFT hole (two copies
 * disagreeing) and opened a SILENT-REDEFINITION one (one token rewriting four assertions at once).
 * The check conscripted into guarding it — `collisionsWithin` in `paginationState.crossRow.test.ts` —
 * cannot do that job, and the last unit's claim that it "will redden on any legitimate rail-count
 * change" is FALSE. `collisionsWithin` is a UNIQUENESS check, not a VALUE check: it fires only when a
 * mutated constant lands on another number of the SAME row, and the live sets are `{1,3,0}` against
 * `{4,2,7}` and `{1,3,0}` against `{6,5,11}`. The two kills that unit recorded — `railSkeletons = 4`
 * and `NO_SKELETONS = 2` — landed exactly on `pageCount` and `currentPage`, which is the ONLY reason
 * they killed; two data points inside the kill set were read as a property of the whole set. Set
 * `railSkeletons: 8`, or `sheetSkeletons: 9`, or `NO_SKELETONS: 9`, and nothing collides in either
 * row, the constants are excluded from `collisionsAcross` by design, and the suite stays green while
 * the expected value has been rewritten in two files and four assertions — in cases `.skip`ped for
 * the whole RED phase, so undetectable until green.
 *
 * WHY IT IS LIVE AND IN ITS OWN FILE. Live because the three stub-driven files are skipped for the
 * whole RED phase, so a skipped guard against a RED-phase edit is prose again; `crossRow.test.ts` and
 * this file are the only things that run today. Its own file because the seam in this suite is by
 * SUBJECT: `crossRow.test.ts`'s subject is what the two laid-out ROWS hold jointly, and these
 * constants are precisely the values that file excludes from its cross-row half (both rows name the
 * same `1`/`3`/`0`). The design surface is a different subject, and it keeps `crossRow.test.ts`'s
 * remaining headroom for the companion case chartered against its own collision expectation.
 *
 * WHAT IT DOES NOT CLAIM. It does not make the numbers RIGHT — both sides are authored here, so a
 * wrong-but-deliberate change is a two-file edit rather than an impossible one. Its whole job is to
 * make the edit DELIBERATE and visible. The mockup is the actual source (`mockups/desktop/
 * 02-measuring.html:46-48` is three rail `.skeleton` divs; `:53` is the one `.sheet.measuring`), and
 * the Selenium leg keeps a THIRD independent copy of the `3` in
 * `acceptance/statements/frontend/editor/pagination_measuring_locators.py:77`
 * (`EXPECTED_RAIL_SKELETON_COUNT = 3`), compared with this one by nothing — a cross-LANGUAGE binding
 * no vitest case can close. Both are flagged for their own steps, not absorbed here.
 *
 * The spread is safe in this direction and only in this direction. Spreading `MEASURING_SURFACE` into
 * a `PaginationViewState` expectation is ruled out twice over, because it deletes the key list from
 * an assertion that has to stay readable as a whole object. Here the constant object IS the subject,
 * so `toStrictEqual` over the spread is what makes the check exhaustive over its members: adding a
 * fourth member to `MEASURING_SURFACE`, or removing one, fails here rather than passing unnoticed.
 * (That covers members of this object only — routing a brand-new top-level constant through it is the
 * separate name-keyed-map exhaustiveness step.) `NO_SKELETONS` is a bare scalar with no key of its
 * own, so it is given one here rather than being tested by a second assertion that could be deleted
 * on its own.
 */
describe('the measuring surface, as a set of decided design numbers', () => {
  it('holds exactly the counts the mockup shows, changed only by editing this expectation too', () => {
    expect({ ...MEASURING_SURFACE, zero: NO_SKELETONS }).toStrictEqual({
      sheetSkeletons: 1,
      railSkeletons: 3,
      zero: 0,
    })
  })
})
