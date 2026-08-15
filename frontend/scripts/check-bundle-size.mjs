// The bundle-size gate. Runs as the tail of `npm run build`, over the dist/ that build just
// produced — see scripts/bundleBudget.mjs for the budgets and why they exist.
import { gzipSync } from 'node:zlib'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { budgetProblems } from './bundleBudget.mjs'

const here = dirname(fileURLToPath(import.meta.url))

// Overridable only through an explicit CLI flag, so the self-test can point this at a fixture
// directory. Not an environment variable: an ambient value exported by a runner would redirect the
// real check while printing the same OK line.
const flag = process.argv.slice(2).find((arg) => arg.startsWith('--dist='))
const dist = flag ? resolve(flag.slice('--dist='.length)) : resolve(here, '../dist/assets')

// A missing dist/ is the gate being unable to run, not a pass. Exiting 0 here would make
// `npm run build` green on a build that produced nothing.
if (!existsSync(dist)) {
  console.error(`No build output at ${dist}.`)
  console.error('Run this through `npm run build`, which produces it.')
  process.exit(1)
}

// Compressed at level 9 rather than the default 6: it is within a fraction of a percent of what a
// CDN with brotli/gzip serves, and it is deterministic across Node versions.
const assets = readdirSync(dist)
  .filter((name) => name.endsWith('.js') || name.endsWith('.css'))
  .map((name) => ({
    name,
    gzipBytes: gzipSync(readFileSync(join(dist, name)), { level: 9 }).length,
  }))

const problems = budgetProblems(assets)

if (problems.length > 0) {
  console.error('Bundle size: the build no longer fits its budgets.')
  console.error(problems.join('\n'))
  process.exit(1)
}

const measured = assets
  .map(({ name, gzipBytes }) => `${name} ${(gzipBytes / 1024).toFixed(1)} kB`)
  .join(', ')
console.log(`Bundle size OK (gzipped) — ${measured}`)
