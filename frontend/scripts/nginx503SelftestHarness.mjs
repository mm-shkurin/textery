// The scaffolding behind check-nginx-503.selftest.mjs: how a fixture conf is built and how the guard
// is invoked. Split out so the self-test file itself is nothing but its cases — the cases are the
// part a reader has to audit, and they were being read past a screen of temp-dir plumbing.
//
// Judging a run (exit code + quoted offender) is not here; that is the same in both gate self-tests
// and lives in selftestRunner.mjs.
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { checkVerdict, runNodeScript } from './selftestRunner.mjs'

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
export function runGuard({ dir, marker = MONOREPO_MARKER, deployNotes, owedItems, backend } = {}) {
  const flags = [
    ...(dir === undefined ? [] : [`--dir=${dir}`]),
    ...(marker ? [`--monorepo-marker=${marker}`] : []),
    ...(deployNotes === undefined ? [] : [`--deploy-notes=${deployNotes}`]),
    ...(owedItems === undefined ? [] : [`--owed-items=${owedItems}`]),
    ...(backend === undefined ? [] : [`--backend=${backend}`]),
  ]
  return runNodeScript(GUARD, flags)
}

function fixtureDir(confs) {
  const dir = mkdtempSync(join(tmpdir(), 'nginx-503-guard-'))
  for (const [name, contents] of Object.entries(confs)) writeFileSync(join(dir, name), contents)
  return dir
}

// `confs: null` means the directory itself is absent — a path under a temp parent that does exist,
// which is what MOVED confs look like, as opposed to a repository that never had any.
export function expectVerdict({ what, confs, code, quotes = [], marker = MONOREPO_MARKER, deployNotes, owedItems, backend }) {
  const missing = confs === null
  const parent = missing ? mkdtempSync(join(tmpdir(), 'nginx-503-gone-')) : null
  const dir = missing ? join(parent, 'moved') : fixtureDir(confs)

  checkVerdict({ what, result: runGuard({ dir, marker, deployNotes, owedItems, backend }), code, quotes })

  rmSync(parent ?? dir, { recursive: true, force: true })
}
