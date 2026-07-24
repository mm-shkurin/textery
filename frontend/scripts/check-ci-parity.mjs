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

// In the split repo there IS no monorepo workflow — `frontend/` is the root there, and the
// counterpart file simply does not exist. Nothing to compare is not a failure; the same command
// has to be safe to run in both repository shapes or it cannot live in package.json.
if (!existsSync(MONOREPO)) {
  console.log('CI parity skipped — no monorepo workflow here (standalone repository shape).')
  process.exit(0)
}

const standalone = npmScripts(STANDALONE)
const monorepo = npmScripts(MONOREPO)

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
