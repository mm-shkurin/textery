// Copy the UI test cases into this repository, from the monorepo.
//
// `frontend/` is republished as its own repository (gitverse `slide_frontend`), and
// `ProductSpecification/` does not travel with it. The written cases — preconditions, steps,
// expected results, per story — therefore existed for the team and for nobody reading the
// published repo: a reviewer cloning it saw 960 automated tests and no test cases at all, which is
// a zero on a criterion worth as much as two code criteria together.
//
// Copies, not moves. `ProductSpecification/stories/*/tests/` stays the source of truth: it is
// where `/test-spec` writes and where the story workflow reads. Every file written here carries a
// banner saying so, so an edit lands upstream instead of in a copy the next sync overwrites.
//
// Only `02_UI_Tests` — the API, load, infrastructure, security and integration suites belong to
// the backend repository, which publishes its own copy the same way
// (`backend/scripts/sync_test_cases.py`).
//
// Run it before pushing a release:
//
//     node scripts/sync-test-cases.mjs           # write
//     node scripts/sync-test-cases.mjs --check   # fail if the copy is stale
//
// `--check` is a monorepo pre-release step, not this repo's CI: in the split repository the source
// directory does not exist and the script says so rather than failing a pipeline that cannot
// possibly fix it.

import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SOURCE_ROOT = join(FRONTEND_ROOT, '..', 'ProductSpecification', 'stories')
const TARGET_ROOT = join(FRONTEND_ROOT, 'docs', 'testing')
const UI_SUITE = '02_UI_Tests'

const banner = (source) =>
  `<!-- COPIED FILE. Source of truth: ${source}\n` +
  `     Regenerate with \`node scripts/sync-test-cases.mjs\` from the monorepo.\n` +
  `     Edits made here are overwritten by the next sync. -->\n\n`

function markdownUnder(dir) {
  const found = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) found.push(...markdownUnder(full))
    else if (entry.endsWith('.md') && entry.startsWith(UI_SUITE)) found.push(full)
  }
  return found
}

function pairs() {
  const out = []
  for (const story of readdirSync(SOURCE_ROOT).sort()) {
    const tests = join(SOURCE_ROOT, story, 'tests')
    if (!existsSync(tests)) continue
    for (const source of markdownUnder(tests).sort()) {
      out.push({ source, target: join(TARGET_ROOT, story, relative(tests, source)) })
    }
  }
  return out
}

const rendered = ({ source }) =>
  banner(relative(join(FRONTEND_ROOT, '..'), source).split('\\').join('/')) +
  readFileSync(source, 'utf8')

function main(checkOnly) {
  if (!existsSync(SOURCE_ROOT)) {
    console.log(`${SOURCE_ROOT} is absent — this is the published repository, nothing to sync.`)
    return 0
  }
  const all = pairs()
  if (all.length === 0) {
    console.error(`no UI test cases found under ${SOURCE_ROOT}`)
    return 1
  }
  const stale = all.filter(
    (pair) => !existsSync(pair.target) || readFileSync(pair.target, 'utf8') !== rendered(pair),
  )
  if (checkOnly) {
    if (stale.length > 0) {
      console.error(`${stale.length} of ${all.length} test-case files are stale or missing:`)
      for (const pair of stale.slice(0, 20)) {
        console.error(`  ${relative(FRONTEND_ROOT, pair.target).split('\\').join('/')}`)
      }
      return 1
    }
    console.log(`${all.length} test-case files are in sync.`)
    return 0
  }
  // Full rebuild: a story renamed or a suite deleted upstream must not leave an orphan here — a
  // test case the jury reads and the team no longer maintains.
  if (existsSync(TARGET_ROOT)) rmSync(TARGET_ROOT, { recursive: true })
  for (const pair of all) {
    mkdirSync(dirname(pair.target), { recursive: true })
    writeFileSync(pair.target, rendered(pair), 'utf8')
  }
  console.log(`wrote ${all.length} test-case files into docs/testing`)
  return 0
}

process.exit(main(process.argv.includes('--check')))
