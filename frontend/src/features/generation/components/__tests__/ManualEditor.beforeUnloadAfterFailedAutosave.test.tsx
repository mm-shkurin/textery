import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import * as documentApi from '../../api/documentApi'
import {
  dispatchBeforeUnload,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

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
  useAutosaveFakeTimers()

  it('keeps preventing unload after a debounced autosave rejects', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockRejectedValue(new Error('network down'))

    await typeAndFireAutosave('hello world')

    // The autosave failed and its banner is up — the gate that proves this ran the failure path.
    // A generic Error is neither SessionExpiredError nor VersionConflictError, so describeSaveFailure
    // returns exactly the network-default copy: assert that text, not mere presence.
    expect(screen.getByTestId('me-save-error')).toHaveTextContent(SAVE_ERROR_MESSAGE)

    // The document is still unsaved, so the guard must still cancel a beforeunload event.
    expect(dispatchBeforeUnload()).toBe(true)
  })
})
