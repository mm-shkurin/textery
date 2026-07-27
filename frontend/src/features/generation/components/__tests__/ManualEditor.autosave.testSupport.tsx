import { afterEach, beforeEach, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

// Debounced-autosave debounce interval (ms). Single source of truth shared by the E3.1
// (autosave) and E3.2 (failed autosave) fake-timer tests so both advance the same boundary.
export const AUTOSAVE_DEBOUNCE_MS = 1000

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

// Renders a ManualEditor whose initial createDocument has already resolved to a fresh draft at
// version 7 — the common starting point for the autosave-failure scenarios.
export async function renderCreatedDocument() {
  vi.mocked(documentApi.createDocument).mockResolvedValue({
    documentId: 'doc-1',
    status: 'draft',
    version: 7,
  })
  render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
  await flushMicrotasks()
}

// Types text into the editor, fires the input event, and crosses the debounce boundary so the
// single debounced autosave fires and its promise settles.
export async function typeAndFireAutosave(text: string) {
  const contentArea = screen.getByTestId('editor-content-area')
  contentArea.textContent = text
  await act(async () => {
    fireEvent.input(contentArea)
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
  })
  await flushMicrotasks()
}
