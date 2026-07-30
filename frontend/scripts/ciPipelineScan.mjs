// Reading a workflow file as a list of gates, for check-ci-parity.mjs.
//
// The naive version of this — one regex for `run: npm run <script>` over the whole file — answers
// "is the gate NAMED here", which is a strictly weaker question than "does the gate RUN". A step can
// be present and dead three cheap ways, and every one of them is what a person under release
// pressure reaches for, because each looks temporary: `if: false`, `continue-on-error: true`, or the
// npm script itself reduced to a no-op in package.json. So a step is only counted when nothing in
// its own block neutralizes it, and the script bodies are checked separately.
import { readFileSync } from 'node:fs'

// A step begins at a `- ` list item and runs to the next one, so `if:` and `continue-on-error:`
// stay attached to the step they modify — a whole-file scan cannot tell whose they are, and that is
// exactly the distinction being made. A step ends where the indentation stops being deeper than the `- ` that opened it. Without that
// bound, the NEXT JOB's keys are swallowed into the previous job's last step: a second job carrying
// the idiomatic `if: github.event_name == 'push'` made the first job's final gate read as
// neutralized, and CI hard-failed pointing at a step nobody had touched.
function steps(contents) {
  const chunks = []
  let depth = null

  for (const line of contents.split('\n')) {
    const indent = line.search(/\S/)
    if (indent === -1) continue

    if (/^\s*-\s/.test(line)) {
      chunks.push({ lines: [line], depth: indent })
      depth = indent
    } else if (depth !== null && indent > depth) {
      chunks[chunks.length - 1].lines.push(line)
    } else {
      depth = null
    }
  }

  return chunks.map((chunk) => chunk.lines.join('\n'))
}

// A job-level `if:` or `continue-on-error:` neutralizes every step under it, and lives ABOVE the
// first `- `, where step chunking cannot see it. Conditioning the whole job is cheaper than
// conditioning eight steps and reads as ordinary workflow hygiene, which is exactly why it needs
// saying. Attribution matters as much as detection: a SECOND job carrying the idiomatic
// `if: github.event_name == 'push'` must not neutralize the first job's gates.
//
// Jobs are found by indentation rather than parsed: under `jobs:`, each key at the shallowest depth
// opens one, and that job's own keys sit between there and its steps.
function jobs(contents) {
  const lines = contents.split('\n')
  const jobsAt = lines.findIndex((line) => /^\s*jobs:\s*$/.test(line))
  if (jobsAt === -1) return [{ header: '', body: contents }]

  const body = lines.slice(jobsAt + 1).filter((line) => line.search(/\S/) !== -1)
  const jobDepth = body.length > 0 ? body[0].search(/\S/) : 0
  const found = []

  for (const line of body) {
    const indent = line.search(/\S/)
    if (indent === jobDepth && /^\s*[\w-]+:\s*$/.test(line)) {
      found.push({ header: [], steps: [] })
      continue
    }
    if (found.length === 0) continue
    const job = found[found.length - 1]
    if (job.steps.length > 0 || /^\s*-\s/.test(line)) job.steps.push(line)
    else job.header.push(line)
  }

  return found.map(({ header, steps }) => ({ header: header.join('\n'), body: steps.join('\n') }))
}

// `npm ci` and the docker build are setup and packaging, not quality gates, and the docker job
// exists only in the monorepo shape — so only `npm run <script>` counts. Both the block style
// (`- name:` then `run:`) and the inline style (`- run: npm run x`) are matched: a reformat between
// them is not a change in what CI does, and treating one as absent would fail loudly on a file that
// is plainly correct.
const RUNS_NPM_SCRIPT = /(?:^|\n)\s*-?\s*run:\s*npm run (\S+)/

// What makes a named step not a gate. `if:` is included in every form, not just `if: false` — a
// step conditioned on a branch or an input is a gate that does not run HERE, and the project lands
// commits directly on working branches, so `if: github.ref == 'refs/heads/main'` would silently
// exempt every one of them.
const NEUTRALIZED = /(?:^|\n)\s*(if:|continue-on-error:\s*true)/

export function scanPipeline(path) {
  const contents = readFileSync(path, 'utf8')
  const active = []
  const neutralized = []

  for (const job of jobs(contents)) {
    const jobIsDead = NEUTRALIZED.test(`\n${job.header}`)
    for (const step of steps(job.body)) {
      const match = step.match(RUNS_NPM_SCRIPT)
      if (!match) continue
      if (jobIsDead || NEUTRALIZED.test(step)) neutralized.push(match[1])
      else active.push(match[1])
    }
  }

  return { active: active.sort(), neutralized: neutralized.sort() }
}

// The floor names gates; their bodies live in package.json, which the workflow files never mention.
// Reducing `check:ingress` to `true`, or dropping the self-test half of it, leaves both pipelines
// and the floor untouched and green while the gate stops gating — the same deletability the floor
// was added to close, one layer down. `mustContain` pins the part of a composite body that the
// floor's stated reason actually depends on.
export function bodyProblems(packageJsonPath, required) {
  const scripts = JSON.parse(readFileSync(packageJsonPath, 'utf8')).scripts ?? {}
  const problems = []

  for (const { script, mustContain = [] } of required) {
    const body = scripts[script]
    if (!body) {
      problems.push(`  npm run ${script} — no such script in package.json`)
      continue
    }
    for (const fragment of mustContain) {
      if (!body.includes(fragment)) {
        problems.push(`  npm run ${script} — no longer runs ${fragment} (body: ${body})`)
      }
    }
  }

  return problems
}
