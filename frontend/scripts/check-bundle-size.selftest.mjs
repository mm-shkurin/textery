// The bundle gate's guard.
//
// A size check is the easiest gate in the repository to make vacuous: point it at the wrong
// directory, filter the asset list to nothing, or invert the comparison, and it prints a
// reassuring OK over any build at all. Every one of those is a case below, driven against fixture
// dist directories filled with incompressible bytes so a size is a size and not a compression
// artifact.
import { fileURLToPath } from 'node:url'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { BUDGETS } from './bundleBudget.mjs'
import { checkVerdict, reportAndExit, runNodeScript } from './selftestRunner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const CHECK = resolve(here, 'check-bundle-size.mjs')

// Random-looking but DETERMINISTIC bytes: gzip must not shrink them, or a fixture asked to be
// 200 kB arrives as 12 kB and every over-budget case passes while asserting nothing. Seeded rather
// than Math.random so a failure is reproducible. xorshift32, not a linear congruential generator:
// an LCG's low-order bits cycle with a short period, which gzip finds and compresses 15:1 —
// measured, and it is what this comment is here to stop being rediscovered.
function incompressible(bytes) {
  const out = Buffer.alloc(bytes)
  let state = 0x2f6e2b1
  for (let i = 0; i < bytes; i += 1) {
    state ^= state << 13
    state ^= state >>> 17
    state ^= state << 5
    out[i] = (state >>> 0) & 0xff
  }
  return out
}

// The filename a budget describes, derived from its own pattern rather than from a hand-written
// table: adding a budget must not require editing this file, or the day someone adds one they get
// a self-test failure about a fixture and learn to distrust it. `.*` stands for the content hash.
function filenameFor(pattern) {
  const name = pattern.source.replace(/^\^|\$$/g, '').replace(/\.\*/g, 'aaaaaaaa')
  const built = name.replace(/\\(.)/g, '$1')
  if (!pattern.test(built)) throw new Error(`cannot build a filename matching ${pattern}`)
  return built
}

// One file per budget, sized as a fraction of what that budget allows. `factor` scales all of them
// at once, which is what makes the under/over pair a single knob rather than a table of numbers
// that has to be re-tuned whenever a budget moves.
function distWith(factor, extra = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'bundle-size-'))
  for (const { pattern, maxGzipKb } of BUDGETS) {
    writeFileSync(
      join(dir, filenameFor(pattern)),
      incompressible(Math.round(maxGzipKb * 1024 * factor)),
    )
  }
  for (const [name, bytes] of Object.entries(extra)) {
    writeFileSync(join(dir, name), incompressible(bytes))
  }
  return dir
}

function expect({ what, dir, code, quotes = [] }) {
  checkVerdict({ what, result: runNodeScript(CHECK, [`--dist=${dir}`]), code, quotes })
  rmSync(dir, { recursive: true, force: true })
}

expect({
  what: 'a build comfortably inside every budget passes',
  dir: distWith(0.5),
  code: 0,
  quotes: ['Bundle size OK'],
})

expect({
  what: 'a chunk over its budget fails and names the file and both numbers',
  dir: distWith(1.5),
  code: 1,
  quotes: ['over its', 'kB budget', 'index-aaaaaaaa.js'],
})

// The case a naive gate misses entirely: nothing existing grew, a whole new chunk appeared.
expect({
  what: 'an asset with no budget fails rather than being ignored',
  dir: distWith(0.5, { 'vendor-bbbbbbbb.js': 400 * 1024 }),
  code: 1,
  quotes: ['vendor-bbbbbbbb.js', 'has no budget'],
})

// The mirror image, and the one that makes the whole suite non-vacuous: if the check quietly
// matched nothing it would pass every case above too.
expect({
  what: 'a budget that matches no asset fails rather than passing vacuously',
  dir: mkdtempSync(join(tmpdir(), 'bundle-size-')),
  code: 1,
  quotes: ['no asset matches'],
})

// Not a pass: an empty or absent dist is the gate being unable to run, and `npm run build` must
// not go green on a build that produced nothing.
checkVerdict({
  what: 'a missing dist directory is a failure, not an empty pass',
  result: runNodeScript(CHECK, [`--dist=${join(tmpdir(), 'bundle-size-does-not-exist')}`]),
  code: 1,
  quotes: ['No build output at'],
})

reportAndExit({
  subject: 'Bundle size',
  subjectIs: 'check-bundle-size.mjs',
  script: 'scripts/check-bundle-size.mjs',
  tail: 'under budget, over budget, an unbudgeted chunk, a budget matching nothing, and a missing dist',
})
