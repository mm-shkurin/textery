import { describe, expect, it } from 'vitest'
import measuringSource from './paginationState.measuring.test.ts?raw'
import laidOutSource from './paginationState.laidOut.test.ts?raw'

/**
 * Story 10, UI scenario 1.1 — THE SITES, not the values.
 *
 * `paginationState.designNumbers.test.ts` pins what `MEASURING_SURFACE` and `NO_SKELETONS` HOLD.
 * It does not pin — and its header wrongly implied it did — that the six skeleton-count assertions
 * in `paginationState.measuring.test.ts` and `paginationState.laidOut.test.ts` still READ those
 * constants. Those are lines in two OTHER files, and until this case existed nothing executable
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
 * case. So every `sheetSkeletonCount:` / `railSkeletonCount:` assignment in the two files is
 * collected IN ORDER with its right-hand side and compared as one object: a re-typed literal, a
 * deleted assertion, an added one, a renamed constant, and a swapped field→constant pairing each
 * move a member of that list.
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
 * make an edit at the assertion site VISIBLE. It is scoped to the skeleton counts, which are the
 * fields the fixture supplies; `pageCount` / `currentPage` reach their assertions through
 * `FONT_GATE_ROW` / `VARIED_GEOMETRY_ROW` and are guarded from the value side by
 * `paginationState.crossRow.test.ts`'s derivation check, which DOES run against the numbers. It
 * says nothing about the acceptance layer's third copy of the `3` in
 * `acceptance/statements/frontend/editor/pagination_measuring_locators.py:77`, which is
 * cross-language and has its own step, nor about the mockup. It reads only these two files: a
 * seventh skeleton assertion written into a THIRD file is outside its window entirely.
 *
 * IT IS FAIL-CLOSED UNDER REFORMATTING, AND THE FAILURE READS AS A DELETION. This was probed rather
 * than assumed, because a source-text check silently defeated by whitespace is prose again. Every
 * shape that is not exactly `<field>: <expression>,` on one trimmed line — a line wrap, a doubled
 * space, a trailing comment, `MEASURING_SURFACE['railSkeletons']` in bracket form — drops that site
 * from the collected list rather than admitting it, so the list SHORTENS and `toStrictEqual` fails.
 * All six variants were run; all six redden. The `3`-behind-a-comment and `3`-across-a-line-wrap
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
 */

/**
 * The sources arrive through Vite's `?raw` suffix rather than through `node:fs`. Three reasons, in
 * order of weight. `tsconfig.app.json` covers `src` with `"types": ["vite/client"]` and no `node`,
 * so `readFileSync` / `resolve` / `process.cwd()` do not typecheck here at all — an earlier draft of
 * this file ran green under vitest, which strips types, while `tsc -b --noEmit` reported five errors
 * against it; the repair is not to add `"node"` to the app tsconfig, which would make `process.env`
 * legal in frontend source. Second, `?raw` is resolved by the module graph, so a wrong or moved path
 * fails at TRANSFORM time with a resolution error rather than at assertion time. Third, it removes
 * the `process.cwd()` dependency, which silently assumed vitest is always invoked from `frontend/`.
 * `import.meta.url` was not an option either: under the jsdom environment this suite runs in it is
 * not a `file:` URL and `fileURLToPath` throws at import time.
 */
const MEASURING_FILE = 'paginationState.measuring.test.ts'
const LAID_OUT_FILE = 'paginationState.laidOut.test.ts'

const SOURCES: Readonly<Record<string, string>> = {
  [MEASURING_FILE]: measuringSource,
  [LAID_OUT_FILE]: laidOutSource,
}

const SKELETON_ASSIGNMENT = /^((?:sheet|rail)SkeletonCount): (.+),$/
const FIXTURE_IMPORT = /^import \{ (.+) \} from '\.\/laidOutRows\.fixture'$/

/**
 * Comment bodies are dropped before matching. Both headers discuss these fields in prose — e.g.
 * "emitting `sheetSkeletonCount: 1`" in `measuring.test.ts` — and a guard that counted a sentence
 * as an assertion site would be satisfied by the very literal it exists to forbid.
 */
const codeLinesOf = (fileName: string): readonly string[] =>
  SOURCES[fileName]
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => !line.startsWith('*') && !line.startsWith('/'))

const matchesOf = (fileName: string, pattern: RegExp): readonly RegExpExecArray[] =>
  codeLinesOf(fileName)
    .map((line) => pattern.exec(line))
    .filter((match): match is RegExpExecArray => match !== null)

interface FixtureUsage {
  readonly fixtureImports: readonly string[]
  readonly skeletonAssignments: readonly string[]
}

const fixtureUsageIn = (fileName: string): FixtureUsage => ({
  fixtureImports: matchesOf(fileName, FIXTURE_IMPORT).map(([, specifiers]) => specifiers),
  skeletonAssignments: matchesOf(fileName, SKELETON_ASSIGNMENT).map(
    ([, field, expression]) => `${field}: ${expression}`,
  ),
})

describe('the skeleton-count assertions, as sites that must read the shared constants', () => {
  it('states every skeleton count by naming a fixture constant, never by re-typing its value', () => {
    expect({
      [MEASURING_FILE]: fixtureUsageIn(MEASURING_FILE),
      [LAID_OUT_FILE]: fixtureUsageIn(LAID_OUT_FILE),
    }).toStrictEqual({
      [MEASURING_FILE]: {
        fixtureImports: ['FONT_GATE_ROW, MEASURING_SURFACE, NO_SKELETONS'],
        skeletonAssignments: [
          'sheetSkeletonCount: MEASURING_SURFACE.sheetSkeletons',
          'railSkeletonCount: MEASURING_SURFACE.railSkeletons',
          'sheetSkeletonCount: NO_SKELETONS',
          'railSkeletonCount: NO_SKELETONS',
        ],
      },
      [LAID_OUT_FILE]: {
        fixtureImports: ['NO_SKELETONS, VARIED_GEOMETRY_ROW'],
        skeletonAssignments: [
          'sheetSkeletonCount: NO_SKELETONS',
          'railSkeletonCount: NO_SKELETONS',
        ],
      },
    })
  })
})
