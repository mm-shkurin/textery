import { afterEach, beforeEach, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import type { SaveDocumentResult } from '../../api/documentApi'
import { AUTOSAVE_DEBOUNCE_MS } from '../../hooks/useAutosave'

// Debounced-autosave debounce interval (ms). Re-exported from the hook rather than redeclared:
// the tests must advance the boundary PRODUCTION uses, so retuning the debounce fails the timer
// tests loudly instead of letting them advance a stale 1000 and silently keep passing.
export { AUTOSAVE_DEBOUNCE_MS } from '../../hooks/useAutosave'

// The document the shared fixture creates. Assertions reference these instead of re-hardcoding
// 'doc-1'/7, so the fixture and every expectation that quotes it move together.
export const CREATED_DOCUMENT_ID = 'doc-1'
export const CREATED_VERSION = 7

// A generous timer advance for the H9.3 failure-taxonomy tests: big enough that the whole
// capped-backoff retry schedule plays out inside it, so assertions never hardcode green's exact
// per-attempt delays. Shared by the retry/expired-session/queued-edit suites (single source).
export const RETRY_WINDOW_MS = 60_000

// Fake-timer settle: drain the pending microtask queue (resolved/rejected save promises,
// their .then/.catch, and the React state updates they schedule) without advancing wall
// clock. Must run under vi.useFakeTimers(); wraps in act() so the flushed updates commit.
export async function flushMicrotasks() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}

// Installs the fake-timer + silenced-console.error lifecycle shared by every autosave-failure
// suite: fake timers on for each test, all mocks restored/cleared and real timers back after.
// Call once inside a describe block — it registers the beforeEach/afterEach hooks at that scope.
export function useAutosaveFakeTimers() {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    vi.useRealTimers()
  })
}

// A promise whose settlement the test controls, so a save can be held "in flight" while further
// edits land. Exposes BOTH resolve and reject: the coalesce/out-of-order suites drive the resolve
// path, the failure suites drive the reject path. The no-op .catch keeps a rejection from
// surfacing as an unhandled rejection before the hook attaches its own handler.
export interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (reason: unknown) => void
}

export function defer<T = SaveDocumentResult>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  promise.catch(() => {})
  return { promise, resolve, reject }
}

// Renders a ManualEditor whose initial createDocument has already resolved to a fresh draft at
// version 7 — the common starting point for the autosave-failure scenarios.
export async function renderCreatedDocument() {
  vi.mocked(documentApi.createDocument).mockResolvedValue({
    documentId: CREATED_DOCUMENT_ID,
    status: 'draft',
    version: CREATED_VERSION,
  })
  render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
  await flushMicrotasks()
}

// Replaces the editor's text and fires the input event — one user edit, WITHOUT crossing the
// debounce boundary. Split out from typeAndFireAutosave because the coalescing suites need an
// edit to land mid-flight while the clock stays put.
export async function typeIntoEditor(text: string) {
  const contentArea = screen.getByTestId('editor-content-area')
  contentArea.textContent = text
  await act(async () => {
    fireEvent.input(contentArea)
  })
}

// Advances past the debounce boundary so a pending debounced autosave fires, then settles its
// promise.
export async function crossDebounceBoundary() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
  })
  await flushMicrotasks()
}

// Types text into the editor, fires the input event, and crosses the debounce boundary so the
// single debounced autosave fires and its promise settles.
export async function typeAndFireAutosave(text: string) {
  await typeIntoEditor(text)
  await crossDebounceBoundary()
}
