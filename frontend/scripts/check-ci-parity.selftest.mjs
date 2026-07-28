// The parity check's guard.
//
// check-ci-parity.mjs decides whether eight CI gates exist at all, and until now nothing tested it:
// narrow REQUIRED, invert isBelowFloor's return, or break the path resolution, and `ci:parity`
// prints OK forever while the pipelines it vouches for run nothing. That is the same disease the
// sibling nginx guard was given a self-test for — this file is the same remedy, one script over.
//
// Cases are driven against FIXTURE workflows written to a temp dir, so the real ones are never
// touched, and generated from REQUIRED itself so a gate cannot be added without a case.
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { REQUIRED } from './ciRequiredGates.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const CHECK = resolve(here, 'check-ci-parity.mjs')

const step = (script) => `      - name: ${script}\n        run: npm run ${script}\n`
const workflow = (scripts) => `jobs:\n  gate:\n    steps:\n${scripts.map(step).join('')}`
const ALL = REQUIRED.map(({ script }) => script)

// A package.json whose bodies satisfy every mustContain, so a case fails for the reason it names
// rather than because the fixture forgot a fragment.
const packageJson = (overrides = {}) => {
  const scripts = Object.fromEntries(
    REQUIRED.map(({ script, mustContain = [] }) => [script, `node ${[script, ...mustContain].join(' ')}`]),
  )
  return JSON.stringify({ scripts: { ...scripts, ...overrides } })
}

function run({ standalone = ALL, monorepo = ALL, pkg = packageJson(), raw = {} }) {
  const dir = mkdtempSync(join(tmpdir(), 'ci-parity-'))
  const paths = { standalone: join(dir, 'standalone.yml'), monorepo: join(dir, 'monorepo.yml'), pkg: join(dir, 'package.json') }

  if (standalone !== null) writeFileSync(paths.standalone, raw.standalone ?? workflow(standalone))
  if (monorepo !== null) writeFileSync(paths.monorepo, raw.monorepo ?? workflow(monorepo))
  writeFileSync(paths.pkg, pkg)

  const flags = [`--standalone=${paths.standalone}`, `--monorepo=${paths.monorepo}`, `--package=${paths.pkg}`]
  try {
    const stdout = execFileSync(process.execPath, [CHECK, ...flags], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
    return { code: 0, output: stdout, dir }
  } catch (error) {
    return { code: error.status, output: `${error.stdout ?? ''}${error.stderr ?? ''}`, dir }
  }
}

const failures = []
let casesRun = 0

function expect({ what, code, quotes = [], ...setup }) {
  casesRun += 1
  const result = run(setup)
  if (result.code !== code) {
    failures.push(`  ${what}\n     expected exit ${code}, got ${result.code}. Output:\n${result.output}`)
  }
  for (const quote of quotes) {
    if (!result.output.includes(quote)) {
      failures.push(`  ${what} — quotes ${JSON.stringify(quote)}\n     absent from:\n${result.output}`)
    }
  }
  rmSync(result.dir, { recursive: true, force: true })
}

expect({ what: 'two complete, identical pipelines pass', code: 0 })

// The floor's whole reason for existing: removing a gate from BOTH files keeps the sameness
// comparison green, so only a named list can notice. One case per gate, generated from the list.
for (const { script } of REQUIRED) {
  const without = ALL.filter((name) => name !== script)
  expect({
    what: `dropping \`${script}\` from both pipelines fails`,
    standalone: without,
    monorepo: without,
    code: 1,
    quotes: [`npm run ${script}`],
  })
}

// Neutering is cheaper than deleting and looks temporary, which is why it is what gets reached for.
expect({
  what: 'a gate behind `if:` counts as missing',
  raw: { monorepo: `jobs:\n  gate:\n    steps:\n${ALL.map((s) => `      - name: ${s}\n        if: false\n        run: npm run ${s}\n`).join('')}` },
  code: 1,
  quotes: ['present but behind'],
})

expect({
  what: 'a gate marked continue-on-error counts as missing',
  raw: { monorepo: `jobs:\n  gate:\n    steps:\n      - name: typecheck\n        continue-on-error: true\n        run: npm run typecheck\n${ALL.filter((s) => s !== 'typecheck').map(step).join('')}` },
  code: 1,
  quotes: ['present but behind'],
})

// The workflows name gates; package.json holds their bodies, and hollowing one there leaves both
// pipelines and the floor untouched.
expect({
  what: 'a required script missing from package.json fails',
  pkg: JSON.stringify({ scripts: Object.fromEntries(ALL.filter((s) => s !== 'build').map((s) => [s, `node ${s}`])) }),
  code: 1,
  quotes: ['no such script in package.json'],
})

expect({
  what: 'a composite script that lost its pinned half fails',
  pkg: packageJson({ 'check:ingress': 'node scripts/check-nginx-503.mjs' }),
  code: 1,
  quotes: ['no longer runs check-nginx-503.selftest.mjs'],
})

// The original job: the two pipelines drifting apart.
expect({
  what: 'a gate present in only one pipeline fails as drift',
  monorepo: [...ALL, 'extra:gate'],
  pkg: packageJson({ 'extra:gate': 'node extra' }),
  code: 1,
  quotes: ['CI drift'],
})

// Both repository shapes that legitimately have one file, plus the one that has neither.
expect({ what: 'the split-repo shape skips the comparison but keeps the floor', monorepo: null, code: 0, quotes: ['Required gates present'] })
expect({ what: 'the split-repo shape still fails below the floor', monorepo: null, standalone: ALL.filter((s) => s !== 'lint'), code: 1, quotes: ['npm run lint'] })
expect({ what: 'a monorepo workflow with no standalone copy fails', standalone: null, code: 1, quotes: ['is not'] })
expect({ what: 'neither workflow present is a clean skip', standalone: null, monorepo: null, code: 0, quotes: ['no frontend workflow here at all'] })

// Generating from REQUIRED means an entry cannot exist without a case — and deleting an entry
// deletes its case too, so the list is pinned by name as well.
if (ALL.join() !== 'typecheck,test:coverage,build,lint,format:check,audit,ci:parity,check:ingress') {
  failures.push(`  the required-gate list changed to: ${ALL.join()}`)
}

if (failures.length > 0) {
  console.error('CI parity self-test: the parity check does not behave as its callers assume.')
  console.error(failures.join('\n'))
  console.error('Fix check-ci-parity.mjs — do not relax these cases to make this pass.')
  process.exit(1)
}

console.log(`CI parity self-test OK — ${casesRun} cases: one per required gate, plus if:/`)
console.log('continue-on-error neutering, package.json hollowing, drift, and all three shapes.')
