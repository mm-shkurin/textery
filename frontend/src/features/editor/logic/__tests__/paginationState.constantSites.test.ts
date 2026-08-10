import { describe, expect, it } from 'vitest'
import { fixtureUsageIn, LAID_OUT_FILE, MEASURING_FILE } from './fixtureUsage.source'

/**
 * Story 10, UI scenario 1.1 — THE SITES, not the values.
 *
 * `paginationState.designNumbers.test.ts` pins what `MEASURING_SURFACE` and `NO_SKELETONS` HOLD.
 * It does not pin — and its header wrongly implied it did — that the count assertions in
 * `paginationState.measuring.test.ts` and `paginationState.laidOut.test.ts` still READ the
 * declarations they are stated in. Those are lines in two OTHER files, and until this case existed nothing executable
 * looked at them. Edit `measuring.test.ts:100` to `railSkeletonCount: 3` and the whole suite stayed
 * green: `designNumbers` passes (the fixture is untouched), `collisionsWithin` passes (it refutes
 * against `SURFACE_CONSTANTS`, never against the assertion), and the drift hole that the sharing
 * was introduced to close is reopened in one token — inside a `.skip`ped case, so invisible until
 * green. Verified by mutation in both directions before this file was written: the edit SURVIVES at
 * HEAD with zero failures and is killed here.
 *
 * WHY IT IS A SOURCE-TEXT CHECK AND NOT A VITEST CASE OVER VALUES. The claim being guarded is about
 * how an expectation is WRITTEN, not about what any function returns. `railSkeletonCount: 3` and
 * `railSkeletonCount: MEASURING_SURFACE.railSkeletons` evaluate to the same number today — that is
 * exactly the defect: they are indistinguishable to every runtime check and differ only in what
 * happens on the NEXT design change. No assertion over `derivePaginationState`'s output can tell
 * them apart, and no assertion over the fixture can either. The subject is the two files' text, so
 * the text is what is read.
 *
 * WHY IT IS LIVE. The three stub-driven cases it guards are `it.skip`ped for the whole RED phase.
 * A skipped guard against a RED-phase edit is prose again, which is the mistake this scenario has
 * now made five times; this file reads the two files' own text and needs neither the stub nor an
 * unskip to fire.
 *
 * WHY THE WHOLE ASSIGNMENT LIST, RATHER THAN "the constant is mentioned somewhere". A check that
 * merely greps for `MEASURING_SURFACE` in each file passes while a seventh assertion is added with
 * a raw literal, or while an existing one is retyped and the import is left in place by another
 * case. So every assignment of a PINNED field in the two files is collected IN ORDER with its
 * right-hand side and compared as one object: a re-typed literal, a deleted assertion, an added one,
 * a renamed constant, and a swapped field→constant pairing each move a member of that list.
 *
 * WHY THE PINNED FIELDS ARE `pageCount` AND `currentPage` AS WELL AS THE TWO SKELETON COUNTS — AND
 * A CORRECTION TO WHAT THIS HEADER USED TO SAY. The first version of this file matched only
 * `(?:sheet|rail)SkeletonCount` and justified the omission by asserting that `pageCount` /
 * `currentPage` "reach their assertions through `FONT_GATE_ROW` / `VARIED_GEOMETRY_ROW` and are
 * guarded from the value side by `paginationState.crossRow.test.ts`'s derivation check". THAT
 * SENTENCE WAS FALSE, in precisely the way the header it was written to replace was false.
 * `crossRow.test.ts:126` derives from `row.blockHeights` and compares the result against
 * `row.pageCount` — the FIXTURE'S declared field. It never reads either test file's assertion, and
 * neither does anything else. `measuring.test.ts:184-185` and `laidOut.test.ts:80-81` are the same
 * construct this file exists for: a fixture value read BY NAME at an assertion site. Retype
 * `pageCount: 4` at `measuring.test.ts:184` and, measured rather than argued, the whole suite stays
 * green — `crossRow` untouched (the fixture did not move), `designNumbers` untouched (it pins only
 * the surface constants), this file untouched under the old pattern (wrong field name), and all six
 * skeleton lines byte-identical. All four of those mutants (`pageCount: 4` / `currentPage: 2` at
 * `measuring.test.ts:184-185`, `pageCount: 6` / `currentPage: 5` at `laidOut.test.ts:80-81`)
 * SURVIVED with zero failures before the alternation was added; each is killed now. The incident
 * they ship is a reader on sheet 3 of a six-page document reading "Страница 5 из 4" — a readout
 * frozen to one fixture's numbers, with every test that could see it derived from those same
 * numbers.
 *
 * `pageCount: null` and `currentPage: null` at `measuring.test.ts:97-98` are therefore legitimate
 * members of the expected list, not omissions. The measuring phase's second Then is "no page count
 * is displayed", and a literal `null` is where that absence is DECIDED — there is no fixture value
 * to name, and the pin belongs at the assertion. They are listed so that an implementation-shaped
 * edit replacing either with a fixture read (or with `undefined`, or with `0`) moves a member of
 * this list rather than passing quietly.
 *
 * WHY THE IMPORT IS PINNED ALONGSIDE THE ASSIGNMENTS. The assignment list alone reads a NAME, and a
 * name is only worth as much as where it is bound. Replacing
 * `import { MEASURING_SURFACE, NO_SKELETONS } from './laidOutRows.fixture'` with a local
 * `const MEASURING_SURFACE = { sheetSkeletons: 1, railSkeletons: 3 }` leaves all six assertion lines
 * BYTE-IDENTICAL: the assignment half of this check passes, `designNumbers` passes (the fixture is
 * untouched), `collisionsWithin` passes (it refutes against the fixture's `SURFACE_CONSTANTS`), and
 * the sharing this whole file exists to protect is severed with nothing red — the file's own defect
 * class, reproduced one level up in the thing that was supposed to close it. Measured, not argued:
 * that mutation passed the first draft of this case. So each file's fixture import specifier list is
 * collected too, as a LIST, so that deleting the import outright fails as loudly as editing it.
 * Keeping the import AND shadowing it locally is not a third option — that is a TypeScript
 * redeclaration error and dies at `tsc --noEmit`.
 *
 * WHAT IT DOES NOT CLAIM. It does not check that the right-hand sides are the RIGHT constants —
 * `designNumbers` owns the values, and both files here are authored in this repo, so a
 * wrong-but-deliberate change remains a two-file edit rather than an impossible one. Its job is to
 * make an edit at the assertion site VISIBLE. It says nothing about the acceptance layer's third
 * copy of the `3` in
 * `acceptance/statements/frontend/editor/pagination_measuring_locators.py:77`, which is
 * cross-language and has its own step, nor about the mockup. It reads only these two files: a
 * seventh skeleton assertion written into a THIRD file is outside its window entirely.
 *
 * IT IS FAIL-CLOSED UNDER REFORMATTING, AND THE FAILURE READS AS A DELETION. This was probed rather
 * than assumed, because a source-text check silently defeated by whitespace is prose again. Every
 * shape that is not exactly `<field>: <expression>,` on one trimmed line reddens this case — but by
 * TWO different mechanisms, and an earlier version of this paragraph claimed only the first for all
 * of them, which was wrong where it mattered least and would have been read as a guarantee where it
 * mattered most. A line wrap and a trailing comment (`pageCount: 4, // frozen`) fail the line regex
 * outright and DROP the site, so the list SHORTENS. A doubled space (`pageCount:  4,`) and
 * `MEASURING_SURFACE['railSkeletons']` in bracket form are both MATCHED — `(.+)` swallows the extra
 * space and the brackets alike — and surface as a CHANGED member (`pageCount:  4`) rather than a
 * missing one. All variants were re-run against the regex directly; every one reddens, so the
 * fail-closed claim stands and only its mechanism is restated here. The `3`-behind-a-comment and `3`-across-a-line-wrap
 * attacks are therefore caught, but they surface as a MISSING member, not as a changed one — read a
 * short list here as "an assertion is no longer in the recognised form", which includes having been
 * re-typed, and go look at the site. Two consequences a reader must not "repair" by loosening the
 * regex. First, the strictness is load-bearing: widen it to tolerate wrapping and the trailing-
 * comment attack starts passing. Second, the repo's own formatter is the authority on that one
 * shape and agrees with it — `measuring.test.ts` and `laidOut.test.ts` are `prettier --check` clean
 * at the pinned form, and the widest of the six sites is 59 columns against a 100-column
 * `printWidth`, so `npm run format` cannot redden this case.
 *
 * IT WILL REDDEN ON LEGITIMATE EDITS, AND THAT IS THE DESIGN. Move a case between these two files,
 * add a third laid-out case, rename a constant, or merely TRANSPOSE two adjacent skeleton keys
 * inside one expectation — the list is ordered, and `toStrictEqual` over the state object does not
 * care about key order, so that last one is a pure reformat with no runtime meaning and it fails
 * here anyway (verified). The correct repair in every case is to update the expectation below in
 * the same commit, having looked at what moved. It is NOT repaired by loosening the match or
 * deleting the case. It is deliberately brittle in the one dimension — assertion-site text — that
 * every other check in this suite is blind to.
 *
 * HOW THE TWO FILES ARE READ lives in `./fixtureUsage.source` — the `?raw` imports, the pinned-field
 * and fixture-import regexes, and the comment-stripping line filter, with their own rationale. That
 * module is mechanics only; the claim, and every mutation that measured it, is stated here. The
 * split was forced by the 200-line ceiling: this case is designed to redden on exactly the edits
 * that lengthen its expectation, so the ingestion had to leave for the next correct repair to fit.
 */

describe('the fixture-supplied assertions, as sites that must read the shared declarations', () => {
  it('states every count by naming a fixture constant or a row field, never by re-typing its value', () => {
    expect({
      [MEASURING_FILE]: fixtureUsageIn(MEASURING_FILE),
      [LAID_OUT_FILE]: fixtureUsageIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: {
        fixtureImports: ['FONT_GATE_ROW, MEASURING_SURFACE, NO_SKELETONS'],
        pinnedAssignments: [
          'pageCount: null',
          'currentPage: null',
          'sheetSkeletonCount: MEASURING_SURFACE.sheetSkeletons',
          'railSkeletonCount: MEASURING_SURFACE.railSkeletons',
          'pageCount: FONT_GATE_ROW.pageCount',
          'currentPage: FONT_GATE_ROW.currentPage',
          'sheetSkeletonCount: NO_SKELETONS',
          'railSkeletonCount: NO_SKELETONS',
        ],
      },
      [LAID_OUT_FILE]: {
        fixtureImports: ['NO_SKELETONS, VARIED_GEOMETRY_ROW'],
        pinnedAssignments: [
          'pageCount: VARIED_GEOMETRY_ROW.pageCount',
          'currentPage: VARIED_GEOMETRY_ROW.currentPage',
          'sheetSkeletonCount: NO_SKELETONS',
          'railSkeletonCount: NO_SKELETONS',
        ],
      },
    })
  })
})
