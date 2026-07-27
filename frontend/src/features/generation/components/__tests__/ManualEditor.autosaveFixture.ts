import { vi } from 'vitest'
import { act } from '@testing-library/react'
import {
  CREATED_VERSION,
  RETRY_WINDOW_MS,
  flushMicrotasks,
} from './ManualEditor.autosave.testSupport'

// The autosave FIXTURE vocabulary: the text a failure suite types, the HTML it expects on the wire,
// and the OCC versions those writes carry. A plain .ts module rather than more exports on
// ManualEditor.autosave.testSupport.tsx — that file exports a component-rendering helper, so every
// non-component export added to it trips react(only-export-components). Nothing here needs JSX.

// The paragraph wrapper Tiptap's schema puts around one line of typed text. Naming the relationship
// is what keeps `typeIntoEditor(SAVED_PLAIN)` and the `saveDocument(_, SAVED_CONTENT, _)` argument
// assertion from drifting apart: nothing else enforces that the text a test types and the HTML it
// expects on the wire are the same edit.
export const asParagraph = (text: string) => `<p>${text}</p>`

// The three-step fixture the dirty-guard failure suites share: a baseline line the server confirms,
// the edit made on top of it whose save fails, and a later revision used to prove the write path is
// still alive after the guard settled. Shared rather than respelled per file because those suites
// are deliberately written as INVERSE assertions over one fixture — a per-file copy is exactly how
// two tests that must stay opposite drift into quietly testing the same thing.
export const SAVED_PLAIN = 'hello world'
export const EDITED_PLAIN = 'hello world edited'
export const REVISED_PLAIN = 'hello world again'
export const SAVED_CONTENT = asParagraph(SAVED_PLAIN)
export const EDITED_CONTENT = asParagraph(EDITED_PLAIN)
export const REVISED_CONTENT = asParagraph(REVISED_PLAIN)

// The versions the baseline save and a later successful save confirm. Derived from CREATED_VERSION
// rather than written as bare 8 and 9: the OCC tuples the suites assert are only meaningful as
// "one past what the fixture started at", and retuning CREATED_VERSION must not leave them
// asserting a fiction that still passes.
export const SAVED_VERSION = CREATED_VERSION + 1
export const RETRY_VERSION = SAVED_VERSION + 1

// Runs the whole capped-backoff retry schedule to completion and settles whatever it fired, plus
// any stale debounce armed during the wait. Extracted because the act/advanceTimersByTimeAsync/
// flushMicrotasks composition is infrastructure the failure suites repeated verbatim — and because
// RETRY_WINDOW_MS is a detail of HOW the schedule is drained, not something a test narrative should
// have to name.
export async function playOutRetrySchedule() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
  })
  await flushMicrotasks()
}
