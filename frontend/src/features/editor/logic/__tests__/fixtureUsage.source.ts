import measuringSource from './paginationState.measuring.test.ts?raw'
import laidOutSource from './paginationState.laidOut.test.ts?raw'

/**
 * Source ingestion for `paginationState.constantSites.test.ts` and
 * `paginationState.assignmentShape.test.ts` — the MECHANICS of reading the two sibling test files'
 * text. The claims being guarded, and every measurement behind them, are documented in those files'
 * headers; this module holds only the how. It was split out at 194 of the repo's 200-line ceiling:
 * `constantSites` grows its expectation AND its header on every legitimate edit it is designed to
 * redden on (a third laid-out case, a seventh skeleton assertion), so leaving the ingestion there
 * made the next correct repair a file-size violation.
 *
 * The sources arrive through Vite's `?raw` suffix rather than through `node:fs`. Three reasons, in
 * order of weight. `tsconfig.app.json` covers `src` with `"types": ["vite/client"]` and no `node`,
 * so `readFileSync` / `resolve` / `process.cwd()` do not typecheck here at all — an earlier draft
 * ran green under vitest, which strips types, while `tsc -b --noEmit` reported five errors against
 * it; the repair is not to add `"node"` to the app tsconfig, which would make `process.env` legal in
 * frontend source. Second, `?raw` is resolved by the module graph, so a wrong or moved path fails at
 * TRANSFORM time with a resolution error rather than at assertion time. Third, it removes the
 * `process.cwd()` dependency, which silently assumed vitest is always invoked from `frontend/`.
 * `import.meta.url` was not an option either: under the jsdom environment this suite runs in it is
 * not a `file:` URL and `fileURLToPath` throws at import time.
 *
 * The imports stay HERE rather than being threaded in as arguments from the test: passing the text
 * in would move the resolution back to the caller and re-create the ingestion surface this split
 * removes, while buying nothing the test can see.
 */
export const MEASURING_FILE = 'paginationState.measuring.test.ts'
export const LAID_OUT_FILE = 'paginationState.laidOut.test.ts'

/**
 * The two names above are the whole legal domain, so every helper takes THIS rather than `string`.
 * A typo'd or moved file name is then a compile error instead of `Cannot read properties of
 * undefined` from `codeLinesOf`, and it makes the callers' per-file expected records total.
 */
export type SourceFile = typeof MEASURING_FILE | typeof LAID_OUT_FILE

const SOURCES: Readonly<Record<SourceFile, string>> = {
  [MEASURING_FILE]: measuringSource,
  [LAID_OUT_FILE]: laidOutSource,
}

/**
 * The pinned-field alternation is spelled ONCE, here, and every pattern that needs it is built from
 * this string. It used to be spelled twice — once in `PINNED_ASSIGNMENT` and once in a `PINNED_FIELD`
 * used to strip the field back off the joined text. That second spelling could drift from the first,
 * and `String.replace` fails OPEN when it does: a non-matching strip returns the text unchanged, so
 * `pageCount: NO_SKELETONS` would have been tested as a right-hand side and surfaced as a mystery
 * re-typed-value failure rather than as "the two patterns disagree". The field is now carried
 * through as a capture group and never re-derived from the joined string.
 *
 * `PINNED_ASSIGNMENT` itself is deliberately narrow, and NOT to be widened — see the fail-closed
 * section of `constantSites`' header. Anything that is not exactly `<field>: <expression>,` on one
 * trimmed line DROPS the site from the collected list rather than admitting it, which is what makes
 * the trailing-comment and line-wrap attacks redden instead of pass.
 */
const PINNED_FIELDS = '(?:pageCount|currentPage|(?:sheet|rail)SkeletonCount)'
const PINNED_ASSIGNMENT = new RegExp(`^(${PINNED_FIELDS}): (.+),$`)
const FIXTURE_IMPORT = /^import \{ (.+) \} from '\.\/laidOutRows\.fixture'$/

/**
 * The two openers below are what let a caller read the expectation BLOCKS and the CASES out of the
 * text instead of hand-typing how many there are. They are matched on the same trimmed,
 * comment-stripped lines as `PINNED_ASSIGNMENT` and are equally fail-closed:
 * `expect(state).toMatchObject({`, an expected object hoisted to module scope, or an assertion
 * severed from its `expect` all yield NO match, so the count SHRINKS rather than being admitted.
 */
const EXPECTATION_OPENER = /^expect\(state\)\.toStrictEqual\(\{$/
const CASE_OPENER = /^it(?:\.skip)?\(/

/**
 * A right-hand side names a SCREAMING_SNAKE constant, a lowercase field read off one, or the literal
 * `null` — and nothing else. See `assignmentShape`' header for why `null` is admitted by name and why
 * widening this to tolerate a bare number would delete that file rather than repair it.
 */
const NAMED_VALUE = /^(?:[A-Z][A-Z0-9_]*(?:\.[a-z][A-Za-z0-9]*)?|null)$/

/**
 * Comment bodies are dropped before matching. Both headers discuss these fields in prose — e.g.
 * "emitting `sheetSkeletonCount: 1`" in `measuring.test.ts` — and a guard that counted a sentence
 * as an assertion site would be satisfied by the very literal it exists to forbid.
 */
const codeLinesOf = (fileName: SourceFile): readonly string[] =>
  SOURCES[fileName]
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => !line.startsWith('*') && !line.startsWith('/'))

const matchesOf = (fileName: SourceFile, pattern: RegExp): readonly RegExpExecArray[] =>
  codeLinesOf(fileName)
    .map((line) => pattern.exec(line))
    .filter((match): match is RegExpExecArray => match !== null)

interface PinnedSite {
  readonly field: string
  readonly expression: string
}

const pinnedSitesIn = (fileName: SourceFile): readonly PinnedSite[] =>
  matchesOf(fileName, PINNED_ASSIGNMENT).map(([, field, expression]) => ({ field, expression }))

interface FixtureUsage {
  readonly fixtureImports: readonly string[]
  readonly pinnedAssignments: readonly string[]
}

export const fixtureUsageIn = (fileName: SourceFile): FixtureUsage => ({
  fixtureImports: matchesOf(fileName, FIXTURE_IMPORT).map(([, specifiers]) => specifiers),
  pinnedAssignments: pinnedSitesIn(fileName).map(
    ({ field, expression }) => `${field}: ${expression}`,
  ),
})

/**
 * The views below are deliberately NOT members of `FixtureUsage`: `constantSites.test.ts` compares
 * that whole object with `toStrictEqual`, and its subject is WHICH assignments exist, not how they
 * are grouped or whether any is re-typed. Grouping and shape are `assignmentShape.test.ts`' subject.
 */
export const fieldsIn = (fileName: SourceFile): readonly string[] =>
  pinnedSitesIn(fileName).map(({ field }) => field)

export const reTypedValuesIn = (fileName: SourceFile): readonly string[] =>
  pinnedSitesIn(fileName)
    .map(({ expression }) => expression)
    .filter((expression) => !NAMED_VALUE.test(expression))

/**
 * The pinned FIELDS of each file, grouped by the `expect(state).toStrictEqual({` block they sit
 * inside, in source order. This is what makes a caller's positional claim real rather than a slice
 * of a flat list: a block whose pinned lines were deleted is a SHORT GROUP (not four names sliding
 * up from the next block), and a pinned line hoisted ABOVE the first opener belongs to no group and
 * is dropped here while `fieldsIn` still counts it — so the two views disagree and the caller
 * reddens. A line stranded after a block has closed lands in that block, making it LONG. Every
 * failure mode grows or shrinks a group; none is silently absorbed.
 */
export const pinnedFieldBlocksIn = (fileName: SourceFile): readonly (readonly string[])[] => {
  const blocks: string[][] = []
  for (const line of codeLinesOf(fileName)) {
    if (EXPECTATION_OPENER.test(line)) blocks.push([])
    const site = PINNED_ASSIGNMENT.exec(line)
    if (site !== null && blocks.length > 0) blocks[blocks.length - 1].push(site[1])
  }
  return blocks
}

export const expectationBlocksIn = (fileName: SourceFile): number =>
  pinnedFieldBlocksIn(fileName).length

export const caseOpenersIn = (fileName: SourceFile): number =>
  matchesOf(fileName, CASE_OPENER).length
