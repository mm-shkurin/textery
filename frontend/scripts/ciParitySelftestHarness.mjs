// Fixture building for check-ci-parity.selftest.mjs — the workflow and package.json text each case
// is run against, and the temp directory they live in.
//
// Split out when the suite crossed the 200-line file limit. It is the same division the nginx guard
// already makes (nginx503SelftestHarness.mjs): what a fixture LOOKS like is plumbing, and reading
// the cases should not require reading it.
import { fileURLToPath } from 'node:url'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { REQUIRED } from './ciRequiredGates.mjs'
import { checkVerdict, runNodeScript } from './selftestRunner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
export const CHECK = resolve(here, 'check-ci-parity.mjs')

export const step = (script) => `      - name: ${script}\n        run: npm run ${script}\n`
export const workflow = (scripts) => `jobs:\n  gate:\n    steps:\n${scripts.map(step).join('')}`
export const ALL = REQUIRED.map(({ script }) => script)

// A package.json whose bodies satisfy every mustContain, so a case fails for the reason it names
// rather than because the fixture forgot a fragment.
export const packageJson = (overrides = {}) => {
  const scripts = Object.fromEntries(
    REQUIRED.map(({ script, mustContain = [] }) => [
      script,
      `node ${[script, ...mustContain].join(' ')}`,
    ]),
  )
  return JSON.stringify({ scripts: { ...scripts, ...overrides } })
}

function run({ standalone = ALL, monorepo = ALL, pkg = packageJson(), raw = {} }) {
  const dir = mkdtempSync(join(tmpdir(), 'ci-parity-'))
  const paths = {
    standalone: join(dir, 'standalone.yml'),
    monorepo: join(dir, 'monorepo.yml'),
    pkg: join(dir, 'package.json'),
  }

  // `null` means the file is not written at all — the repository shapes where one of the two
  // workflows legitimately does not exist, which is a different case from an empty one.
  if (standalone !== null) writeFileSync(paths.standalone, raw.standalone ?? workflow(standalone))
  if (monorepo !== null) writeFileSync(paths.monorepo, raw.monorepo ?? workflow(monorepo))
  writeFileSync(paths.pkg, pkg)

  const flags = [
    `--standalone=${paths.standalone}`,
    `--monorepo=${paths.monorepo}`,
    `--package=${paths.pkg}`,
  ]
  return { dir, result: runNodeScript(CHECK, flags) }
}

export function expect({ what, code, quotes = [], ...setup }) {
  const { dir, result } = run(setup)
  checkVerdict({ what, result, code, quotes })
  rmSync(dir, { recursive: true, force: true })
}
