// The production-dependency advisory gate. Replaces `npm audit --omit=dev --audit-level=high`,
// which passed by not looking below a line nobody had to justify — see scripts/auditExceptions.mjs
// for why a threshold is the wrong instrument. Every advisory counts here, at every severity, and
// the only way past is a dated entry in the ledger.
import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { problems } from './auditLedger.mjs'

function flag(name) {
  const match = process.argv.slice(2).find((arg) => arg.startsWith(`--${name}=`))
  return match ? match.slice(name.length + 3) : null
}

// `npm audit` exits non-zero when it finds anything, which is the normal case here — the report on
// stdout is what matters, not the code. A crash with no stdout is different in kind: an unreachable
// registry, a corrupt lockfile, an npm that never got to a verdict. That must not read as "no
// advisories found", so it is reported as the gate being unable to run.
function auditReport() {
  const fixture = flag('report')
  if (fixture) return readFileSync(fixture, 'utf8')

  // Retried, because the usual cause of a verdictless crash is a registry blip and the gate runs on
  // every push AND every local pre-commit run. Retrying does NOT weaken it: a reachable registry
  // answers the same on attempt two, so the only outcome that changes is a transient outage that
  // would have reddened a pipeline over nothing. Three attempts, then still fail-closed — the
  // alternative, passing on an unreachable registry, is exactly the "OK over a report nobody read"
  // this gate exists to prevent.
  const attempts = Number(flag('attempts') ?? 3)
  let last = null
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      // A fixed command string through the shell, not an argv array: `npm` on Windows is `npm.cmd`,
      // which Node refuses to spawn directly (EINVAL) since the CVE-2024-27980 fix, and passing an
      // argv array with `shell: true` is the deprecated shape that concatenates arguments unescaped.
      // Nothing here is interpolated, so there is no argument for a shell to mis-split.
      return execSync('npm audit --omit=dev --json', {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'pipe'],
      })
    } catch (error) {
      // A report on stdout IS the answer: `npm audit` exits non-zero whenever it finds anything,
      // which is the normal case here. Never retried — the verdict already arrived.
      const stdout = error.stdout ?? ''
      if (stdout.trim().startsWith('{')) return stdout
      last = error
      if (attempt < attempts) {
        console.error(`Dependency audit did not reach a verdict (attempt ${attempt}); retrying.`)
        sleep(2000 * attempt)
      }
    }
  }
  console.error(`Dependency audit could not run in ${attempts} attempts — not a clean report.`)
  console.error(`  ${last.message.split('\n')[0]}`)
  console.error(`  ${(last.stderr ?? '').trim().split('\n').slice(-3).join('\n  ')}`)
  console.error('Usually an unreachable registry. Rerun with network; do not skip the gate.')
  process.exit(1)
}

// Synchronous on purpose: everything around it is `execSync`, and making this async would turn the
// gate's one straight line into a promise chain for the sake of a sleep between retries.
function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
}

// Overridable so the self-test can hold an expiry date still. Not an environment variable: an
// ambient date exported by a runner would move every deadline in the ledger while printing the same
// OK line, where a flag has to be typed into the step a reader can see.
const today = flag('today') ?? new Date().toISOString().slice(0, 10)

let report
try {
  report = JSON.parse(auditReport())
} catch (error) {
  console.error(`Dependency audit produced no parseable report — ${error.message}`)
  process.exit(1)
}

// The ledger is overridable for the same reason the date is: the self-test has to drive the
// accepted and expired verdicts, and neither can be reached through the real ledger once it is
// empty. Production runs pass no flag and read auditExceptions.mjs.
const ledgerPath = flag('ledger')
const { ACCEPTED } = ledgerPath
  ? await import(pathToFileURL(resolve(ledgerPath)).href)
  : await import('./auditExceptions.mjs')

const found = problems(report, today, ACCEPTED)

if (found.length > 0) {
  console.error('Dependency audit: production advisories that are not accounted for.')
  console.error(found.join('\n'))
  console.error('Do not raise a threshold or delete the gate to make this pass.')
  process.exit(1)
}

const ledger = ACCEPTED.map(
  ({ ghsa, package: pkg, expires }) => `${pkg} ${ghsa} (until ${expires})`,
)
console.log(
  ledger.length === 0
    ? 'Dependency audit OK — no production advisories, and nothing accepted.'
    : `Dependency audit OK — every finding is an accepted, unexpired exception: ${ledger.join(', ')}`,
)
