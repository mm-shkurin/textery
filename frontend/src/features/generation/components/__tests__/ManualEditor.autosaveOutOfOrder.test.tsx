import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  defer,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'
import { DIRTY_STATUS, SAVED_STATUS } from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Scenario E3.3 / H9.2 (07_Editor_Extension_Tests.md §3.3, 02_UI_Tests.md §4.2): two autosaves in
// flight resolving out of order — the shown status and content must reflect the LATEST edit (B),
// and a stale first (A) response must not overwrite the newer state.
//
// This is a LIVE CHARACTERIZATION GUARD, not a red→green cycle. useDocumentSave SERIALIZES saves:
// performSave sets isSavingRef; a save() or autosave landing mid-flight only flips
// saveAgainRequested rather than launching a second concurrent saveDocument. The queued save (B)
// is fired from A's resolve handler with A's returned version and a fresh read of the current
// editor content. So two saveDocument calls are NEVER simultaneously in flight through this path,
// and out-of-order ARRIVAL cannot occur — latest-wins holds by construction. There is nothing to
// implement, so green-frontend is [S]. This test locks the observable guarantee so a future change
// that let a stale A response clobber the newer content or status would fail here.

describe('ManualEditor — out-of-order autosaves reflect the latest edit and content (E3.3/H9.2)', () => {
  // Timers only — this suite deliberately does NOT silence console.error: nothing here rejects, so a
  // console.error appearing would be a real diagnostic worth seeing rather than expected noise.
  useAutosaveFakeTimers()

  it('keeps the latest edit and status when a queued save resolves after a stale first save, and the stale response never clobbers the newer content', async () => {
    await renderCreatedDocument()

    // The first save (A) is held pending so a second edit lands while A is still "in flight".
    const saveA = defer()
    const saveB = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(saveA.promise)
      .mockReturnValueOnce(saveB.promise)

    // Edit #1 → debounce → first autosave (A) fires and stays pending.
    await typeAndFireAutosave('first version')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      '<p>first version</p>',
      CREATED_VERSION,
    )

    // Edit #2 lands while A is still in flight: it must queue a re-save, NOT launch a second
    // concurrent saveDocument. Advancing the debounce here re-enters save() which finds A in
    // flight and only sets the "save again" flag.
    await typeAndFireAutosave('second version')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // A resolves LAST-in-wall-clock but FIRST-in-order, carrying stale server content that differs
    // from what the editor now holds. The resolve handler must NOT adopt it (editor moved on), and
    // must fire the queued save (B) with the LATEST content and A's returned version.
    await act(async () => {
      saveA.resolve({ status: 'saved', version: 8, content: '<p>STALE SERVER</p>' })
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      '<p>second version</p>',
      8,
    )
    // The stale A response did not overwrite the editor's newer content.
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>second version</p>')

    // B — the save for the latest edit — resolves and settles the shown state.
    await act(async () => {
      saveB.resolve({ status: 'saved', version: 9, content: '<p>second version</p>' })
    })
    await flushMicrotasks()

    // Final state reflects the latest edit (B): content preserved, status is exactly "saved".
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>second version</p>')
    // Strict status: the saved element's own text is exactly "Сохранено" (not a substring hit
    // elsewhere), and the dirty status must be gone — a stale-A clobber reverting to dirty fails here.
    expect(screen.getByText(SAVED_STATUS).textContent).toBe(SAVED_STATUS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()
  })
})
