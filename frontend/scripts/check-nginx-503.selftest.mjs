// The guard's guard (Scenario H9.4).
//
// check-nginx-503.mjs is a CI gate whose PASS output and whose broken-no-op output are the same
// line in the log. Narrow its directive list, break the path resolution, or invert the offender
// push, and a step named `nginx 503 guard` prints OK forever — the same "config that looks like a
// gate and gates nothing" failure frontend-ci.yml's own header calls out one layer down.
//
// So the gate is driven against fixture confs here: each case asserts an exit code, and the failing
// ones assert the offending line is actually quoted (an exit 1 with an empty message would still
// pass a bare code check while telling the reader nothing). The mutation checks behind the original
// commits were one-time manual runs; this is what preserves them.
//
// Fixtures are written to a temp dir rather than committed: they exist to be fed to one script, and
// a committed fixture conf under infra/ would be scanned by the real gate itself.
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'

const here = dirname(fileURLToPath(import.meta.url))
const GUARD = resolve(here, 'check-nginx-503.mjs')

// Every fixture carries the back-reference except the case that tests its absence — the guard
// requires one conf in the directory to name the predicate, so omitting it everywhere would make
// every case fail for the wrong reason.
const BACK_REFERENCE = '# see mayHaveLandedServerSide in autosaveRetryPolicy.ts\n'
const CLEAN_CONF = `${BACK_REFERENCE}server {\n    listen 80;\n    location /api/ {\n        proxy_pass http://backend:8000;\n    }\n}\n`

function runGuard(dir) {
  try {
    const stdout = execFileSync(process.execPath, [GUARD], {
      env: { ...process.env, NGINX_503_DIR: dir },
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

function check(what, condition, detail) {
  if (condition) return
  failures.push(`  ${what}\n     ${detail}`)
}

function expectVerdict({ what, confs, code, quotes = [] }) {
  const dir = confs === null ? join(mkdtempSync(join(tmpdir(), 'nginx-503-gone-')), 'moved') : fixtureDir(confs)
  const result = runGuard(dir)

  check(what, result.code === code, `expected exit ${code}, got ${result.code}. Output:\n${result.output}`)
  for (const quote of quotes) {
    check(
      `${what} — quotes ${JSON.stringify(quote)}`,
      result.output.includes(quote),
      `that string is absent from the guard's output:\n${result.output}`,
    )
  }

  rmSync(dir, { recursive: true, force: true })
}

// A conf that proxies to the origin and can answer nothing itself: the only shape that may pass.
expectVerdict({ what: 'a clean conf passes', confs: { 'frontend.conf': CLEAN_CONF }, code: 0 })

// The canonical maintenance one-liner. This is the case the guard shipped unable to catch — it
// matched no directive in the first version and the step printed OK over a conf 503ing every
// request. Pinned first among the failures for that reason.
expectVerdict({
  what: '`return 503` fails',
  confs: { 'frontend.conf': `${BACK_REFERENCE}server {\n    location = /maint { return 503; }\n}\n` },
  code: 1,
  quotes: ['return 503;', '`503`'],
})

expectVerdict({
  what: '`limit_req` fails',
  confs: { 'frontend.conf': `${BACK_REFERENCE}server {\n    limit_req zone=api burst=5;\n}\n` },
  code: 1,
  quotes: ['limit_req zone=api burst=5;'],
})

expectVerdict({
  what: '`proxy_intercept_errors` fails',
  confs: { 'frontend.conf': `${BACK_REFERENCE}server {\n    proxy_intercept_errors on;\n}\n` },
  code: 1,
  quotes: ['proxy_intercept_errors on;'],
})

// The comment-stripping is load-bearing in the other direction too: the real conf's back-reference
// NAMES every scanned directive, so a scan of raw text would fire on the guard's own explanation.
expectVerdict({
  what: 'a comment naming the directives does not fire',
  confs: {
    'frontend.conf': `${BACK_REFERENCE}# do not add limit_req, error_page, return 503 or proxy_next_upstream here\n${CLEAN_CONF}`,
  },
  code: 0,
})

// The pointer is what the hops OUTSIDE this repo have instead of a gate. Deleting it is silent.
expectVerdict({
  what: 'losing the back-reference fails',
  confs: { 'frontend.conf': 'server {\n    listen 80;\n}\n' },
  code: 1,
  quotes: ['mayHaveLandedServerSide'],
})

// Demanded of the DIRECTORY, not each file: a second conf for static caching or a healthcheck
// listener proxies nothing to the origin and has no reason to carry the warning.
expectVerdict({
  what: 'a second conf without the back-reference passes while one conf has it',
  confs: { 'frontend.conf': CLEAN_CONF, 'health.conf': 'server {\n    listen 8081;\n}\n' },
  code: 0,
})

// Both ways of ending up with nothing to scan. The second is the one that used to exit 0 with a
// reassuring line, because a missing directory is ambiguous between "split repo" and "moved".
expectVerdict({ what: 'an empty conf directory fails', confs: {}, code: 1 })
expectVerdict({ what: 'a missing conf directory fails in the monorepo shape', confs: null, code: 1 })

if (failures.length > 0) {
  console.error('nginx 503 guard self-test: the guard does not behave as its callers assume.')
  console.error(failures.join('\n'))
  console.error('Fix check-nginx-503.mjs — do not relax these cases to make this pass.')
  process.exit(1)
}

console.log('nginx 503 guard self-test OK — 9 cases: clean conf, 503 emitters, comments, the')
console.log('back-reference, a second conf, an empty directory, a moved directory.')
