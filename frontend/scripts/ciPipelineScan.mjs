// Reading a workflow file as a list of gates, for check-ci-parity.mjs.
//
// The naive version of this — one regex for `run: npm run <script>` over the whole file — answers
// "is the gate NAMED here", which is a strictly weaker question than "does the gate RUN". A step can
// be present and dead three cheap ways, and every one of them is what a person under release
// pressure reaches for, because each looks temporary: `if: false`, `continue-on-error: true`, or the
// npm script itself reduced to a no-op in package.json. So a step is only counted when nothing in
// its own block neutralizes it, and the script bodies are checked separately.
import { readFileSync } from 'node:fs'

// A step begins at a `- ` list item and runs to the next one. Splitting this way keeps `if:` and
// `continue-on-error:` attached to the step they modify — a whole-file scan cannot tell whose they
// are, and that is exactly the distinction being made.
function steps(contents) {
  const chunks = []
  for (const line of contents.split('\n')) {
    if (/^\s*-\s/.test(line)) chunks.push([line])
    else if (chunks.length > 0) chunks[chunks.length - 1].push(line)
  }
  return chunks.map((chunk) => chunk.join('\n'))
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

  for (const step of steps(contents)) {
    const match = step.match(RUNS_NPM_SCRIPT)
    if (!match) continue
    if (NEUTRALIZED.test(step)) neutralized.push(match[1])
    else active.push(match[1])
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
