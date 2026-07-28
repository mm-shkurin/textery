// Two CI files gate this code, because `frontend/` is published both as a directory of the
// monorepo and as the ROOT of a separate repo (gitverse slide_frontend). Their headers say they
// are "kept in step by hand", and hand-kept parity is the kind that holds until the day it
// matters: the split repo would keep passing an older gate, silently, with nothing red anywhere.
//
// This checks the ONE thing that must match — the set of quality commands each pipeline runs.
// Everything else about the two files is legitimately different (triggers, working-directory,
// cache paths, the docker job that only the monorepo has), so nothing else is compared.
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const STANDALONE = resolve(here, '../.github/workflows/ci.yml')
const MONOREPO = resolve(here, '../../.github/workflows/frontend-ci.yml')

// `run: npm run <script>` only. `npm ci` and the docker build are setup and packaging, not the
// quality gate, and the docker job exists solely in the monorepo shape.
function npmScripts(path) {
  const matches = readFileSync(path, 'utf8').matchAll(/^\s*run:\s*npm run (\S+)/gm)
  return [...matches].map((match) => match[1]).sort()
}

// Sameness is not presence: two identical pipelines that run NOTHING satisfy the comparison below,
// and so does deleting one step from both files in the same commit. That is the shape of the
// failure this file exists to prevent, one level up — every gate here is a step someone under
// release pressure can remove, and the only thing that noticed would be this comparison, which
// removal keeps green.
//
// So the gates are named. Each entry says what is lost when it goes, because a bare list gets
// pruned as clutter and a reason does not.
const REQUIRED = [
  ['typecheck', 'tsc -b; without it a broken build reaches main invisibly (vitest strips types)'],
  ['test:coverage', 'the suite AND the per-file coverage floors, which only fire under --coverage'],
  ['build', 'the one step that proves the app still compiles and bundles'],
  ['lint', 'oxlint at --max-warnings=0'],
  ['format:check', 'a .prettierrc nobody runs is a preference, not a convention'],
  ['audit', 'production dependency advisories at high and above'],
  ['ci:parity', 'this check; a pipeline that drops it can then drift freely'],
  ['check:ingress', 'the nginx 503 guard behind mayHaveLandedServerSide — see that predicate'],
]

function checkFloor(label, path, scripts) {
  const missing = REQUIRED.filter(([script]) => !scripts.includes(script))
  if (missing.length === 0) return false

  console.error(`CI gate missing from ${label}:`)
  for (const [script, why] of missing) console.error(`  npm run ${script} — ${why}`)
  console.error(`  (${path})`)
  return true
}

const standalone = npmScripts(STANDALONE)

// In the split repo there IS no monorepo workflow — `frontend/` is the root there, and the
// counterpart file simply does not exist. Nothing to COMPARE is not a failure; the same command
// has to be safe to run in both repository shapes or it cannot live in package.json. The floor
// still applies to the pipeline that is here, since that is the one gating that repo.
if (!existsSync(MONOREPO)) {
  if (checkFloor('frontend/.github/workflows/ci.yml', STANDALONE, standalone)) {
    console.error('Restore the step; do not remove a gate to make a pipeline pass.')
    process.exit(1)
  }
  console.log('CI parity skipped — no monorepo workflow here (standalone repository shape).')
  console.log(`Required gates present: ${REQUIRED.map(([script]) => script).join(', ')}`)
  process.exit(0)
}

const monorepo = npmScripts(MONOREPO)

const belowFloor = [
  checkFloor('frontend/.github/workflows/ci.yml', STANDALONE, standalone),
  checkFloor('.github/workflows/frontend-ci.yml', MONOREPO, monorepo),
].some(Boolean)

if (belowFloor) {
  console.error('Restore the step; do not remove a gate to make a pipeline pass.')
  process.exit(1)
}

if (standalone.join() !== monorepo.join()) {
  const onlyStandalone = standalone.filter((s) => !monorepo.includes(s))
  const onlyMonorepo = monorepo.filter((s) => !standalone.includes(s))
  console.error('CI drift: the two frontend pipelines no longer run the same npm scripts.')
  console.error(`  frontend/.github/workflows/ci.yml : ${standalone.join(', ') || '(none)'}`)
  console.error(`  .github/workflows/frontend-ci.yml: ${monorepo.join(', ') || '(none)'}`)
  if (onlyStandalone.length) console.error(`  only in the standalone copy: ${onlyStandalone}`)
  if (onlyMonorepo.length) console.error(`  only in the monorepo copy:   ${onlyMonorepo}`)
  console.error('Add the missing step to the other file; do not delete one to make this pass.')
  process.exit(1)
}

console.log(`CI parity OK — both pipelines run: ${monorepo.join(', ')}`)
