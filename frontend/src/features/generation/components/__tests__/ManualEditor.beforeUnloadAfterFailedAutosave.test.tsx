import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import { SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import * as documentApi from '../../api/documentApi'
import { AUTOSAVE_DEBOUNCE_MS, flushMicrotasks } from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

function dispatchBeforeUnload(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

// Scenario H9.3, gap (b) — the beforeunload-still-armed-after-a-failed-autosave hole flagged by the
// E3.2 premortem. A failed autosave must leave the document DIRTY: the work is still only in the
// editor's memory, so the browser's native leave-prompt guard has to stay armed. The behaviour is
// correct today (the reject handler never calls onSaved, so hasUnsavedChanges stays true) but was
// UNGUARDED — a refactor that cleared the dirty flag on failure, or a retry path that optimistically
// marked clean, would silently disarm the guard and let a close discard the unsaved paragraph.
//
// Characterization guard (mirrors the dirty path in ManualEditor.beforeUnloadGuard.test): passes
// today, so its green counterpart is [S].
describe('ManualEditor — the beforeunload guard stays armed after a failed autosave (H9.3 gap b)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('keeps preventing unload after a debounced autosave rejects', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
    await flushMicrotasks()

    vi.mocked(documentApi.saveDocument).mockRejectedValue(new Error('network down'))

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    await act(async () => {
      fireEvent.input(contentArea)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    await flushMicrotasks()

    // The autosave failed and its banner is up — the gate that proves this ran the failure path.
    // A generic Error is neither SessionExpiredError nor VersionConflictError, so describeSaveFailure
    // returns exactly the network-default copy: assert that text, not mere presence.
    expect(screen.getByTestId('me-save-error')).toHaveTextContent(SAVE_ERROR_MESSAGE)

    // The document is still unsaved, so the guard must still cancel a beforeunload event.
    expect(dispatchBeforeUnload()).toBe(true)
  })
})
