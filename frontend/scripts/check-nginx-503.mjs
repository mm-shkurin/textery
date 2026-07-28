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
if (!existsSync(NGINX_DIR)) {
  console.log('nginx 503 guard skipped — no infra/docker/nginx here (standalone repository shape).')
  process.exit(0)
}

// Every directive by which nginx can answer 503 to a request it has already forwarded, or answer it
// on the origin's behalf. `limit_req`/`limit_conn` reject with 503 by default; `error_page` can map
// anything onto a 503 maintenance page; `max_fails` + `proxy_next_upstream` make nginx exhaust an
// upstream group and return 503 without the origin ever answering. `upstream` is listed because it
// is the block the last two require — its presence is the earliest visible signal.
const DIRECTIVES = ['limit_req', 'limit_conn', 'error_page', 'max_fails', 'proxy_next_upstream', 'upstream']

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
for (const name of confs) {
  const contents = readFileSync(join(NGINX_DIR, name), 'utf8')
  const lines = contents
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'))

  for (const line of lines) {
    for (const directive of DIRECTIVES) {
      if (line.includes(directive)) offenders.push(`  ${name}: ${line}   (\`${directive}\`)`)
    }
  }

  // The environment half of the premise has no test at all — only this pointer. Losing it is how
  // the next person adds the directive without ever learning what it breaks.
  if (!contents.includes('mayHaveLandedServerSide')) {
    offenders.push(`  ${name}: lost the back-reference naming mayHaveLandedServerSide`)
  }
}

if (offenders.length > 0) {
  console.error('nginx can now answer 503, and the autosave retry treats 503 as proof the write')
  console.error('never landed — on that answer it can suppress the write, leaving the editor')
  console.error('showing «Сохранено» over content the server never got.')
  console.error(offenders.join('\n'))
  console.error('See frontend/src/features/generation/hooks/autosaveRetryPolicy.ts')
  console.error('(mayHaveLandedServerSide). Change that branch in the same commit, or do not add')
  console.error('the directive.')
  process.exit(1)
}

console.log(`nginx 503 guard OK — ${confs.join(', ')} declare none of: ${DIRECTIVES.join(', ')}`)
