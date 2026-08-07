// The boundary gate's guard.
//
// A gate that walks a directory has one dominant failure mode, and it is not a wrong verdict - it
// is walking nothing. Point it at the wrong root, filter the file list to empty, or stop matching
// the import syntax the codebase actually uses, and it prints "no unlisted cross-feature imports"
// over a tree full of them. Every case below is driven against a fixture src/ tree for that reason,
// and the first one asserts the gate can still say NO.
import { fileURLToPath } from 'node:url'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { ALLOWED_SHARED_TO_FEATURE } from './boundaryRules.mjs'
import { checkVerdict, reportAndExit, runNodeScript } from './selftestRunner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const CHECK = resolve(here, 'check-boundaries.mjs')

// A fixture tree: {relative path: file contents}. Written under a temp src/ so the real one is
// never read and a case cannot pass because the actual codebase happens to be clean.
function treeWith(files) {
  const root = mkdtempSync(join(tmpdir(), 'boundaries-'))
  for (const [path, contents] of Object.entries(files)) {
    const full = join(root, path)
    mkdirSync(dirname(full), { recursive: true })
    writeFileSync(full, contents)
  }
  return root
}

function expect({ what, files, code, quotes = [] }) {
  const root = treeWith(files)
  checkVerdict({ what, result: runNodeScript(CHECK, [`--src=${root}`]), code, quotes })
  rmSync(root, { recursive: true, force: true })
}

expect({
  what: 'one feature importing another fails and names both sides',
  files: {
    'features/projects/components/Card.tsx':
      "import { poll } from '../../generation/hooks/useGeneration'\n",
    'features/generation/hooks/useGeneration.ts': 'export const poll = () => {}\n',
  },
  code: 1,
  quotes: ['features/projects/components/Card.tsx', 'features/generation'],
})

expect({
  what: 'a feature importing shared is allowed',
  files: {
    'features/projects/components/Card.tsx': "import { send } from '../../../shared/api/send'\n",
    'shared/api/send.ts': 'export const send = () => {}\n',
  },
  code: 0,
  quotes: ['Module boundaries OK'],
})

// The session layer is the one cross-feature edge the architecture actually has. Every screen needs
// a signed-in identity, and the alternative is per-feature token handling that disagrees with
// itself about whether a session is still valid.
expect({
  what: 'a feature importing the session layer is allowed',
  files: {
    'features/history/api/historyApi.ts':
      "import { request } from '../../auth/api/authorizedRequest'\n",
    'features/auth/api/authorizedRequest.ts': 'export const request = () => {}\n',
  },
  code: 0,
  quotes: ['Module boundaries OK'],
})

// Upside down by definition, and the reason the exception list exists rather than a blanket
// tolerance: an unlisted one has to be argued for in a file someone reads.
expect({
  what: 'shared importing an unlisted feature fails',
  files: {
    'shared/components/Widget.tsx': "import { thing } from '../../features/projects/projectKey'\n",
    'features/projects/projectKey.ts': 'export const thing = 1\n',
  },
  code: 1,
  quotes: ['shared/components/Widget.tsx', 'boundaryRules.mjs'],
})

// Generated from the ledger, so an entry cannot be added without a case that exercises it - and an
// entry whose `from` path stops existing shows up here rather than as silent dead weight.
for (const entry of ALLOWED_SHARED_TO_FEATURE) {
  const depth = entry.from.split('/').length
  expect({
    what: `the written exception ${entry.from} -> ${entry.to} is allowed`,
    files: {
      [entry.from]: `import { x } from '${'../'.repeat(depth)}${entry.to}'\n`,
      [`${entry.to}.ts`]: 'export const x = 1\n',
    },
    code: 0,
    quotes: ['Module boundaries OK'],
  })
}

// The vacuity case. `export ... from` is the re-export form, and a regex written only for `import`
// misses it entirely - a barrel file could then launder any boundary violation in the codebase.
expect({
  what: 'a cross-feature re-export is caught, not only a plain import',
  files: {
    'features/projects/index.ts': "export { poll } from '../generation/hooks/useGeneration'\n",
    'features/generation/hooks/useGeneration.ts': 'export const poll = () => {}\n',
  },
  code: 1,
  quotes: ['features/generation'],
})

expect({
  what: 'app may import every feature, since wiring them together is what it is',
  files: {
    'app/App.tsx': "import { LoginForm } from '../features/auth/components/LoginForm'\n",
    'features/auth/components/LoginForm.tsx': 'export const LoginForm = () => null\n',
  },
  code: 0,
  quotes: ['Module boundaries OK'],
})

reportAndExit({
  subject: 'Module boundaries',
  subjectIs: 'check-boundaries.mjs',
  script: 'scripts/check-boundaries.mjs',
  tail: 'cross-feature import, shared and session-layer edges, unlisted shared->feature, every written exception, a re-export, and app',
})
