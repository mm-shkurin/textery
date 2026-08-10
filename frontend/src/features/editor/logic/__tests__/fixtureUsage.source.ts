import measuringSource from './paginationState.measuring.test.ts?raw'
import laidOutSource from './paginationState.laidOut.test.ts?raw'

/**
 * Source ingestion for `paginationState.constantSites.test.ts` — the MECHANICS of reading the two
 * sibling test files' text. The claim being guarded, and every measurement behind it, is documented
 * in that file's header; this module holds only the how. It was split out at 194 of the repo's
 * 200-line ceiling: `constantSites` grows its expectation AND its header on every legitimate edit
 * it is designed to redden on (a third laid-out case, a seventh skeleton assertion), so leaving the
 * ingestion there made the next correct repair a file-size violation.
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

const SOURCES: Readonly<Record<string, string>> = {
  [MEASURING_FILE]: measuringSource,
  [LAID_OUT_FILE]: laidOutSource,
}

/**
 * Deliberately narrow, and NOT to be widened — see the fail-closed section of `constantSites`'
 * header. Anything that is not exactly `<field>: <expression>,` on one trimmed line DROPS the site
 * from the collected list rather than admitting it, which is what makes the trailing-comment and
 * line-wrap attacks redden instead of pass.
 */
const PINNED_ASSIGNMENT = /^(pageCount|currentPage|(?:sheet|rail)SkeletonCount): (.+),$/
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

export interface FixtureUsage {
  readonly fixtureImports: readonly string[]
  readonly pinnedAssignments: readonly string[]
}

export const fixtureUsageIn = (fileName: string): FixtureUsage => ({
  fixtureImports: matchesOf(fileName, FIXTURE_IMPORT).map(([, specifiers]) => specifiers),
  pinnedAssignments: matchesOf(fileName, PINNED_ASSIGNMENT).map(
    ([, field, expression]) => `${field}: ${expression}`,
  ),
})
