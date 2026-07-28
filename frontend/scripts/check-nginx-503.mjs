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
import { DIRECTIVES, firstFiring } from './nginx503Directives.mjs'

const here = dirname(fileURLToPath(import.meta.url))

// Both paths are overridable ONLY through explicit CLI flags, and only so the self-test can point
// the guard at fixture confs and at a fabricated repository shape. Deliberately NOT environment
// variables: an ambient NGINX_503_DIR exported by a runner, a sourced .env or a workflow-level
// `env:` block would silently redirect the production scan and print the same reassuring OK line,
// whereas a flag has to be typed into the step that runs it, where a reader sees it.
function flag(name, fallback) {
  const match = process.argv.slice(2).find((arg) => arg.startsWith(`--${name}=`))
  return match ? resolve(match.slice(name.length + 3)) : fallback
}

const NGINX_DIR = flag('dir', resolve(here, '../../infra/docker/nginx'))

// In the split repo (gitverse slide_frontend) `frontend/` is the ROOT and `infra/` does not exist —
// the same shape check check-ci-parity.mjs makes. Nothing to scan is not a failure there; the
// command has to be safe in both shapes or it cannot live in package.json.
//
// The shape is decided by the monorepo workflow, not by NGINX_DIR itself: a missing directory is
// ambiguous between "split repo" and "somebody moved infra/docker/nginx", and skipping on the
// second is the gate failing OPEN with a reassuring line — the more likely of the two, since
// directories get moved more often than emptied.
const MONOREPO_WORKFLOW = flag('monorepo-marker', resolve(here, '../../.github/workflows/frontend-ci.yml'))

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

  // Judged line by line against the whole file: two entries (`upstream`, and the codes an
  // `error_page` maps) are only dangerous in company, and each entry owns its own boundary so the
  // benign forms — an SPA `error_page 404`, a bare `upstream` block — do not fail the build. A
  // guard that is wrong on first contact gets deleted rather than refined.
  const conf = lines.join('\n')
  for (const line of lines) {
    const directive = firstFiring(line, conf)
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
