// The module-boundary gate. Runs as the tail of `npm run lint`, over src/ — see
// scripts/boundaryRules.mjs for the rule and the written exceptions.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative, resolve } from 'node:path'
import { areaOf, isAllowed } from './boundaryRules.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const flag = process.argv.slice(2).find((arg) => arg.startsWith('--src='))
const root = flag ? resolve(flag.slice('--src='.length)) : resolve(here, '../src')

function sourceFiles(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry)
    if (statSync(path).isDirectory()) return sourceFiles(path)
    // Tests are excluded: a test may reach across boundaries to build a fixture, and that is
    // scaffolding rather than a dependency the shipped bundle carries.
    return /\.tsx?$/.test(path) && !path.includes('__tests__') ? [path] : []
  })
}

// Relative specifiers only. A bare `react` or `@tiptap/react` is a package, not an internal
// boundary, and resolving those would mean reading tsconfig paths for no gain here.
const RELATIVE_IMPORT = /(?:^|\n)\s*(?:import|export)[^\n]*?from '(\.[^']+)'/g

const problems = []

for (const file of sourceFiles(root)) {
  const fromRelative = relative(root, file)
  const fromArea = areaOf(fromRelative)

  for (const [, specifier] of readFileSync(file, 'utf8').matchAll(RELATIVE_IMPORT)) {
    const toRelative = relative(root, resolve(dirname(file), specifier))
    const toArea = areaOf(toRelative)
    if (isAllowed({ fromArea, toArea, fromFile: fromRelative, toPath: toRelative })) continue
    problems.push(
      `  ${fromRelative.replace(/\\/g, '/')} imports ${toArea} (${specifier})\n` +
        `    ${fromArea} may import itself, shared, and the session layer. Move the shared part into` +
        ` shared/, or add a row to scripts/boundaryRules.mjs saying why this one is right.`,
    )
  }
}

if (problems.length > 0) {
  console.error(
    'Module boundaries: an import crosses a wall the architecture does not have a door in.',
  )
  console.error(problems.join('\n'))
  process.exit(1)
}

console.log(
  `Module boundaries OK — no unlisted cross-feature imports in ${relative(resolve(here, '..'), root) || 'src'}.`,
)
