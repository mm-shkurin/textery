// The parts of `mayHaveLandedServerSide`'s premise that live OUTSIDE the nginx confs.
//
// The carve-out reads 503 as proof the write never landed, so it can suppress a write on that
// answer. That is a claim about every hop between the browser and the origin — and about the origin
// itself. Two of those claims are checkable from here, read-only:
//
//   1. the ORIGIN emits no 503. `backend/` is the other layer's to edit, but reading it is not
//      editing it, and the frontend is the layer that breaks when the claim lapses. Scanning it is
//      what turns "verified 2026-07-28" — a timestamp with no mechanism behind it — into a fact
//      re-established on every build.
//   2. the pointers survive. The hops with no IaC source have no gate at all; their only carrier is
//      prose, in files that get restructured. Losing that prose is silent.
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

// Skipped wholesale: caches, virtualenvs and build output are not this repo's source, and a `503`
// inside a vendored dependency says nothing about what the origin emits.
const NOT_SOURCE = new Set(['.venv', 'venv', '__pycache__', 'node_modules', '.git', '.pytest_cache', 'htmlcov'])
const SOURCE_FILE = /\.(py|toml|cfg|ini|ya?ml)$/

function sourceFiles(root) {
  const found = []
  for (const entry of readdirSync(root)) {
    if (NOT_SOURCE.has(entry)) continue
    const path = join(root, entry)
    if (statSync(path).isDirectory()) found.push(...sourceFiles(path))
    else if (SOURCE_FILE.test(entry)) found.push(path)
  }
  return found
}

// `\b503\b` and not a bare substring: a port `5030`, a timeout `1503`, a hash or a line count are
// not status codes, and a scan that fails on those gets deleted the first time it fires on one.
// Comments are cut for the same reason a comment cannot arm the conf scan — a line explaining WHY
// no handler returns 503 must not itself trip it.
const STATUS_503 = /\b503\b/
const stripComment = (line) => line.split('#')[0]

export function originEmits503(backendDir) {
  const offenders = []

  for (const path of sourceFiles(backendDir)) {
    const lines = readFileSync(path, 'utf8').split('\n')
    lines.forEach((line, index) => {
      if (STATUS_503.test(stripComment(line))) {
        offenders.push(`  ${path}:${index + 1}: ${line.trim()}`)
      }
    })
  }

  return offenders
}

// Existence AND content. A file that was moved or renamed loses the pointer in the way that looks
// most like housekeeping, and an empty-handed `includes` check would pass over the absence.
export function pointerProblems(files) {
  const problems = []

  for (const { path, label, marker } of files) {
    if (!existsSync(path)) {
      problems.push(`  ${path} does not exist — ${label}`)
    } else if (!readFileSync(path, 'utf8').includes(marker)) {
      problems.push(`  ${path} no longer says ${marker} — ${label}`)
    }
  }

  return problems
}
