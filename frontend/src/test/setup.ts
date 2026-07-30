import '@testing-library/jest-dom'
// Imported from @testing-library/react, not @testing-library/dom: the latter is NOT declared in
// package.json and resolves today only by hoisting through the former, so a lockfile or resolver
// change would break this file. `configure` is re-exported, so this is the same function.
import { configure } from '@testing-library/react'

// Testing Library's default async budget is 1000ms, which is a fine budget for a state flush and
// a bad one for a CHUNK LOAD. `DocumentGenerationFlow` lazy-imports ManualEditor (Tiptap +
// ProseMirror, the heaviest dependency in the tree), so any `findBy*` that waits for the editor
// to mount is waiting on Vite transforming and evaluating that module — measured at ~1.4s when
// the file runs alongside its siblings and comfortably under 1s when it runs alone. That is a
// pass/fail line drawn by machine load rather than by behaviour, and it bit exactly once before
// this was raised (story 18, scenario 2.1's green).
//
// This does NOT weaken any assertion: a `findBy*` whose element never arrives still fails, it
// just takes longer to say so. The cost is paid only by genuinely failing waits.
configure({ asyncUtilTimeout: 5000 })

// jsdom implements no layout, so it lacks the geometry APIs ProseMirror's
// mousedown handler walks (posAtCoords -> posFromElement -> findOffsetInNode).
// Any test that dispatches a real pointer event onto the editor DOM otherwise
// throws an unhandled TypeError deep inside prosemirror-view. Empty rects and a
// null hit-test are the documented "no geometry here" contract, which
// ProseMirror handles gracefully.
if (typeof document.elementFromPoint !== 'function') {
  document.elementFromPoint = () => null
}
const emptyRect = () => ({
  x: 0,
  y: 0,
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: 0,
  height: 0,
  toJSON: () => ({}),
})
if (typeof Range.prototype.getClientRects !== 'function') {
  Range.prototype.getClientRects = () => Object.assign([], { item: () => null })
  Range.prototype.getBoundingClientRect = emptyRect as never
}
