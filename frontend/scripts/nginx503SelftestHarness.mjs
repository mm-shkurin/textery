// The scaffolding behind check-nginx-503.selftest.mjs: how a fixture conf is built, how the guard is
// invoked, how a verdict is recorded. Split out so the self-test file itself is nothing but its
// cases — the cases are the part a reader has to audit, and they were being read past a screen of
// temp-dir and child-process plumbing.
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'

const here = dirname(fileURLToPath(import.meta.url))
const GUARD = resolve(here, 'check-nginx-503.mjs')

// The shape marker the real guard looks for, and a fabricated one this harness WRITES. Every case
// passes the fabricated marker, so it decides the repository shape it runs in rather than inheriting
// the shape of the checkout — the split repo (`frontend/` as root, no infra/, no monorepo workflow)
// has to be exercisable from a monorepo checkout and vice versa.
export const REAL_MONOREPO_MARKER = resolve(here, '../../.github/workflows/frontend-ci.yml')
export const MONOREPO_MARKER = join(mkdtempSync(join(tmpdir(), 'nginx-503-shape-')), 'frontend-ci.yml')
writeFileSync(MONOREPO_MARKER, '# fabricated monorepo marker for the self-test\n')

// Every fixture carries the back-reference except the case that tests its absence — the guard
// requires one conf in the directory to name the predicate, so omitting it everywhere would make
// every case fail for the wrong reason.
export const BACK_REFERENCE = '# see mayHaveLandedServerSide in autosaveRetryPolicy.ts\n'
export const CLEAN_CONF = `${BACK_REFERENCE}server {\n    listen 80;\n    location /api/ {\n        proxy_pass http://backend:8000;\n    }\n}\n`

// A conf whose only content is the one line under test, so each failing case reads as that line and
// nothing else — the scaffolding around it is never what decides the verdict.
export const confDeclaring = (line) => `${BACK_REFERENCE}server {\n    ${line}\n}\n`

// The guard takes both paths as CLI flags, so what it believes about its surroundings is an input
// here. `marker: null` means «pass no flag», leaving the guard to resolve its own defaults — the
// only way to exercise the path resolution CI actually takes.
export function runGuard({ dir, marker = MONOREPO_MARKER } = {}) {
  const flags = [
    ...(dir === undefined ? [] : [`--dir=${dir}`]),
    ...(marker ? [`--monorepo-marker=${marker}`] : []),
  ]
  try {
    const stdout = execFileSync(process.execPath, [GUARD, ...flags], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    return { code: 0, output: stdout }
  } catch (error) {
    return { code: error.status, output: `${error.stdout ?? ''}${error.stderr ?? ''}` }
  }
}

function fixtureDir(confs) {
  const dir = mkdtempSync(join(tmpdir(), 'nginx-503-guard-'))
  for (const [name, contents] of Object.entries(confs)) writeFileSync(join(dir, name), contents)
  return dir
}

const failures = []
let casesRun = 0

export function check(what, condition, detail) {
  if (condition) return
  failures.push(`  ${what}\n     ${detail}`)
}

export function countCase() {
  casesRun += 1
}

// `confs: null` means the directory itself is absent — a path under a temp parent that does exist,
// which is what MOVED confs look like, as opposed to a repository that never had any.
export function expectVerdict({ what, confs, code, quotes = [], marker = MONOREPO_MARKER }) {
  countCase()
  const missing = confs === null
  const parent = missing ? mkdtempSync(join(tmpdir(), 'nginx-503-gone-')) : null
  const dir = missing ? join(parent, 'moved') : fixtureDir(confs)
  const result = runGuard({ dir, marker })

  check(what, result.code === code, `expected exit ${code}, got ${result.code}. Output:\n${result.output}`)
  for (const quote of quotes) {
    check(
      `${what} — quotes ${JSON.stringify(quote)}`,
      result.output.includes(quote),
      `that string is absent from the guard's output:\n${result.output}`,
    )
  }

  rmSync(parent ?? dir, { recursive: true, force: true })
}

// Counted, never hardcoded: a printed constant is how this suite would acquire the disease it was
// written to cure — a case deleted while debugging, and a PASS line that reads identically.
export function reportAndExit(tail) {
  if (failures.length > 0) {
    console.error('nginx 503 guard self-test: the guard does not behave as its callers assume.')
    console.error(failures.join('\n'))
    console.error('Fix check-nginx-503.mjs — do not relax these cases to make this pass.')
    process.exit(1)
  }

  console.log(`nginx 503 guard self-test OK — ${casesRun} cases: ${tail}`)
}
