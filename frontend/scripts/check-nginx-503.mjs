// The executable half of `mayHaveLandedServerSide`'s 503 carve-out (Scenario H9.4).
//
// That predicate reads 503 as PROOF the write was never taken, so on a 503 the autosave keeps its
// memory of the last saved content and a revert inside the backoff window suppresses the write
// entirely (useDocumentSave.ts:133 + the fire-time gate at :140). Safe only while nothing in front
// of the origin emits 503 AFTER accepting a write.
//
// Most of that premise is an environment fact no test can assert — a WAF, a TLS terminator, the
// host/prod-copy proxy. The hop that lives in this repo is a checked-in file, so "the container
// nginx emits no 503" is a plain assertion over its bytes, and prose is the wrong instrument for it.
//
// A node script rather than a vitest case for two reasons: the conf sits OUTSIDE `frontend/`, where
// Vite's fs.allow denies it and `node:fs` needs `@types/node` the app does not carry; and this is a
// repository-shape check like check-ci-parity.mjs, not a unit of app behaviour.
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const NGINX_DIR = resolve(here, '../../infra/docker/nginx')

// In the split repo (gitverse slide_frontend) `frontend/` is the ROOT and `infra/` does not exist —
// the same shape check check-ci-parity.mjs makes. Nothing to scan is not a failure there; the
// command has to be safe in both shapes or it cannot live in package.json.
//
// The shape is decided by the monorepo workflow, not by NGINX_DIR itself: a missing directory is
// ambiguous between "split repo" and "somebody moved infra/docker/nginx", and skipping on the
// second is the gate failing OPEN with a reassuring line — the more likely of the two, since
// directories get moved more often than emptied.
const MONOREPO_WORKFLOW = resolve(here, '../../.github/workflows/frontend-ci.yml')

if (!existsSync(NGINX_DIR)) {
  if (existsSync(MONOREPO_WORKFLOW)) {
    console.error(`nginx 503 guard: ${NGINX_DIR} does not exist, but this IS the monorepo shape`)
    console.error(`(${MONOREPO_WORKFLOW} is here). The confs moved — point this guard and the`)
    console.error('path filter in that workflow at the new location. Skipping would leave the')
    console.error('ingress unscanned while the step still reports OK.')
    process.exit(1)
  }
  console.log('nginx 503 guard skipped — no infra/docker/nginx here (standalone repository shape).')
  process.exit(0)
}

// Every way nginx can answer 503 to a request it has already forwarded, or answer it on the
// origin's behalf. `return 503`/`503` in a rewrite is the canonical maintenance one-liner and the
// most direct of them; `limit_req`/`limit_conn` reject with 503 by default; `error_page` can map
// anything onto a 503 page; `proxy_intercept_errors` hands the origin's own 5xx to those pages;
// `max_fails` + `proxy_next_upstream` make nginx exhaust an upstream group and answer 503 without
// the origin ever replying. `upstream` is listed because it is the block the last two require —
// its presence is the earliest visible signal. The bare status code is scanned as a string: any
// uncommented line mentioning 503 is either an answer or a comment that should have been one.
const DIRECTIVES = [
  '503',
  'limit_req',
  'limit_conn',
  'error_page',
  'proxy_intercept_errors',
  'max_fails',
  'proxy_next_upstream',
  'upstream',
]

const confs = readdirSync(NGINX_DIR).filter((name) => name.endsWith('.conf'))

if (confs.length === 0) {
  console.error(`nginx 503 guard: no .conf found under ${NGINX_DIR} — a moved or renamed conf`)
  console.error('leaves this guard scanning nothing. Point it at the new location.')
  process.exit(1)
}

// A line scan, not an nginx parse: the failure mode is someone ADDING a directive, and scanning raw
// lines catches it inside an `if` block, a `map`, or any nesting a structural check would walk past.
// Comments are stripped first — the conf carries a back-reference NAMING these directives, so a scan
// over the raw text would fire on the guard's own explanation of itself.
const offenders = []
let backReferenced = false
for (const name of confs) {
  const contents = readFileSync(join(NGINX_DIR, name), 'utf8')
  const lines = contents
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'))

  for (const line of lines) {
    // First match only: `upstream` is a substring of `proxy_next_upstream`, so a line carrying one
    // of the compound directives would otherwise be reported twice for the same offence.
    const directive = DIRECTIVES.find((candidate) => line.includes(candidate))
    if (directive) offenders.push(`  ${name}: ${line}   (\`${directive}\`)`)
  }

  if (contents.includes('mayHaveLandedServerSide')) backReferenced = true
}

// Demanded of the DIRECTORY, not of each file: a second conf added later for static caching, a
// healthcheck listener or an admin vhost proxies nothing to the origin and has no reason to carry
// the warning. Per-file, that conf would fail CI accusing its author of losing something that was
// never there — and the predictable answer to that is a pasted comment nobody read.
if (!backReferenced) {
  offenders.push(
    `  no conf under ${NGINX_DIR} names mayHaveLandedServerSide — the hops OUTSIDE this repo` +
      ' have no guard but that pointer, so it has to survive here',
  )
}

if (offenders.length > 0) {
  console.error('nginx can now answer 503, and the autosave retry treats 503 as proof the write')
  console.error('never landed — on that answer it can suppress the write, leaving the editor')
  console.error('showing «Сохранено» over content the server never got.')
  console.error(offenders.join('\n'))
  console.error('See frontend/src/features/generation/hooks/autosaveRetryPolicy.ts')
  console.error('(mayHaveLandedServerSide). Three ways out, in order of preference:')
  console.error('  1. Do not add the directive.')
  console.error('  2. Change that frontend branch in the same commit.')
  console.error('  3. If this line provably CANNOT answer 503 — `error_page 404 /index.html;`, a')
  console.error('     plain `upstream` block with no max_fails/proxy_next_upstream — then the scan')
  console.error('     is over-firing: tighten it here and add the case that pins the boundary.')
  console.error('Deleting this step is not on the list: nothing else guards the premise.')
  process.exit(1)
}

console.log(`nginx 503 guard OK — ${confs.join(', ')} declare none of: ${DIRECTIVES.join(', ')}`)
