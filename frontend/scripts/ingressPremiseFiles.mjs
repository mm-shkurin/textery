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
// `.mypy_cache` earns its place the hard way: it holds `.json` sidecars the SOURCE_FILE filter
// never wanted, and a backend session running mypy in a parallel checkout rewrites it WHILE this
// walks — which is how the stale entry below turned up.
const NOT_SOURCE = new Set([
  '.venv',
  'venv',
  '__pycache__',
  'node_modules',
  '.git',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  'htmlcov',
])
const SOURCE_FILE = /\.(py|toml|cfg|ini|ya?ml)$/

function sourceFiles(root) {
  const found = []
  for (const entry of readdirSync(root)) {
    if (NOT_SOURCE.has(entry)) continue
    const path = join(root, entry)
    // A file that vanishes between readdir and stat is skipped, not fatal. Two sessions share
    // this checkout and the backend one writes tool caches under `backend/`, so the walk races
    // by construction — and an ENOENT here took the whole gate down with a stack trace, which
    // reads as "the ingress premise is broken" when nothing about the premise had changed. A
    // guard that goes red for a reason it is not guarding is a guard that gets ignored.
    let stats
    try {
      stats = statSync(path)
    } catch {
      continue
    }
    if (stats.isDirectory()) found.push(...sourceFiles(path))
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

// The ONE exemption, and it is a narrowing of the claim rather than a hole in it. The claim is
// "no 503 can be the answer to a WRITE"; the container probe is the one route that provably
// cannot answer one. `GET /health` is unauthenticated and deliberately outside `/api/v1` — the
// caller is the orchestrator, and an autosave PUT never resolves to it. Scanning it made the
// guard fire on a route whose 503 is its entire contract, and a guard that fires on correct code
// is a guard someone deletes.
//
// Keyed on a `health` path SEGMENT, not on a filename or on the string `503`: the exemption has
// to survive the router being split into more files, and must not extend to a module that merely
// has "health" in its name (`health_metrics_api.py` is a file, not a segment).
//
// WHAT THIS DOES NOT EXEMPT, written down because the exemption makes it likelier rather than
// safer: a probe answering 503 is consumed by an ORCHESTRATOR, which removes the instance, and a
// load balancer in front of it then answers 503 to requests already in flight — including a write
// the origin had already taken. That hop has no IaC source in this repo and therefore no gate
// (see mayHaveLandedServerSide's chain note). It is the standing argument for dropping the 503
// carve-out entirely — which is the exit that note already names, and which is a behaviour change
// owed to H9.4, not to this scan.
const HEALTH_PROBE_SEGMENT = /(^|[\\/])health([\\/]|$)/

export function originEmits503(backendDir) {
  const offenders = []

  for (const path of sourceFiles(backendDir)) {
    if (HEALTH_PROBE_SEGMENT.test(path.slice(backendDir.length))) continue
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
