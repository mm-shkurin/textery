// The floor a global coverage threshold cannot enforce.
//
// vite.config.ts holds aggregate thresholds, and an aggregate hides exactly one thing: a module
// nobody tests at all. A thousand well-covered lines absorb one uncovered file without moving the
// percentage enough to fail — which is how historyApi.ts sat at 0% while every caller mocked it
// and the suite stayed green for weeks.
//
// So this is not a second quality bar. The numbers are deliberately far below the global ones:
// the question it asks is "did someone add a module and test none of it", not "is this module
// well tested". Raising these to look ambitious would make it a duplicate of the global gate and
// a source of unrelated red builds.
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, relative, resolve } from 'node:path'

const MIN_STATEMENTS = 60
const MIN_BRANCHES = 45

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')
const summaryPath = resolve(root, 'coverage/coverage-summary.json')

if (!existsSync(summaryPath)) {
  console.error(`No coverage summary at ${summaryPath}.`)
  console.error('Run this through `npm run test:coverage`, which produces it.')
  process.exit(1)
}

const summary = JSON.parse(readFileSync(summaryPath, 'utf8'))

const failures = []
for (const [file, totals] of Object.entries(summary)) {
  if (file === 'total') continue
  // Stylesheets appear in the summary because components import them, and they have no statements
  // to cover — every one reports 0%. Coverage is a question about code.
  if (!/\.tsx?$/.test(file)) continue
  const statements = totals.statements.pct
  const branches = totals.branches.pct
  // A file with no branches at all reports 100 for branches in v8's summary, so the branch check
  // only ever fires on files that actually have branches to miss.
  if (statements < MIN_STATEMENTS || branches < MIN_BRANCHES) {
    failures.push({ file: relative(root, file), statements, branches })
  }
}

if (failures.length > 0) {
  console.error(`Per-file coverage floor: ${MIN_STATEMENTS}% statements, ${MIN_BRANCHES}% branches.`)
  for (const failure of failures) {
    console.error(`  ${failure.file} — ${failure.statements}% statements, ${failure.branches}% branches`)
  }
  console.error('Test the module rather than lowering the floor; the floor only catches untested ones.')
  process.exit(1)
}

console.log(`Per-file coverage floor OK across ${Object.keys(summary).length - 1} files.`)
