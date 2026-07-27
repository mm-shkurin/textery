import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  DIRTY_STATUS,
  SAVED_STATUS,
  crossDebounceBoundary,
  defer,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4 — the redundant-trailing-PUT defect confirmed by both review passes on E3.1 green
// (7f2998e). An edit landing DURING an in-flight autosave does two things: it queues a mid-flight
// re-save (saveAgainRequested), and it arms a fresh debounce timer. The queued re-save persists the
// latest content and marks the document clean ("Сохранено"). But the debounce timer armed by that
// same edit is never cleared, so once the clock crosses it a THIRD saveDocument fires on content
// that is already saved — version churn / write amplification, not data loss. There is no
// dirty-check in save()/autosave to suppress it.
//
// The base coalesce behaviour ("continuous typing collapses to one save, not one per keystroke") is
// already pinned by ManualEditor.autosave.test.tsx — "collapses multiple edits within the debounce
// window into a single autosave" — so it is reused here, not duplicated. This file targets only the
// genuinely-failing trailing-PUT defect.
describe('ManualEditor — no redundant trailing autosave after a mid-flight edit already saved (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  it('does not fire a third saveDocument on already-saved content when the stale mid-flight debounce timer elapses, and still autosaves the next real edit', async () => {
    await renderCreatedDocument()

    const firstSave = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSave.promise)
      // Call #2 (the queued mid-flight re-save) echoes edit #2 back at version 9…
      .mockResolvedValueOnce({ status: 'saved', version: 9, content: '<p>hello world</p>' })
      // …and call #3 (the live-autosave proof) echoes ITS OWN content at version 10. Without a
      // separate resolution the fallback would hand call #3 the PREVIOUS content, which the adoption
      // branch in useDocumentSave would then write back into the editor — silently reverting the
      // very edit this assertion is about.
      .mockResolvedValue({ status: 'saved', version: 10, content: '<p>hello world again</p>' })

    // Edit #1 → cross the debounce → autosave #1 fires and stays in flight (isSaving true).
    await typeIntoEditor('hello')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    // Save #1 persists edit #1's serialized content at the version render started from (7).
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      '<p>hello</p>',
      CREATED_VERSION,
    )

    // Edit #2 lands while save #1 is still in flight: it queues a re-save (saveAgainRequested) AND
    // arms a fresh debounce timer (deadline one window out) that nothing later clears.
    await typeIntoEditor('hello world')

    // Resolve the in-flight save WITHOUT advancing the clock: its resolve handler fires the queued
    // re-save (#2) on the latest content, which resolves and marks the document clean.
    await act(async () => {
      firstSave.resolve({ status: 'saved', version: 8, content: '<p>hello</p>' })
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // The queued re-save (#2) persists edit #2's latest content at the version save #1 returned (8),
    // proving OCC version threading — the re-save must carry 8, not the stale 7 it started from.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      8,
    )
    // Strict status: the badge's own text is exactly "Сохранено" (not a substring hit elsewhere)
    // and the dirty badge is gone — the document is clean, which is what makes a third PUT redundant.
    expect(screen.getByText(SAVED_STATUS).textContent).toBe(SAVED_STATUS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()

    // Cross the stale mid-flight debounce boundary. Nothing has changed since the clean save, so no
    // third PUT should fire on unchanged content.
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // ...and the elapsed stale timer must be inert in every observable way: it may not re-dirty the
    // badge, and the adopted server content must still be the latest edit.
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>hello world</p>')
    expect(screen.getByText(SAVED_STATUS).textContent).toBe(SAVED_STATUS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()

    // Suppression must be scoped to already-saved content, NOT a blanket disabling of autosave: a
    // genuine later edit still autosaves, carrying the version threaded from re-save #2's response.
    await typeIntoEditor('hello world again')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      '<p>hello world again</p>',
      9,
    )
  })
})
