import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import { SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import * as documentApi from '../../api/documentApi'
import {
  crossDebounceBoundary,
  defer,
  flushMicrotasks,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4, pre-conditions (a) and (b)(2) — the other side of the dirty guard.
//
// The trailing-PUT suppression must NOT be bought by cancelling the debounce timer inside noteEdit:
// that cancels at ARM time, before anyone knows whether the queued mid-flight re-save will succeed.
// When it FAILS, the debounce is the only writer left — nothing else re-arms until the user types
// again, so a user who stops typing loses the burst. These two tests fail under that fix and pass
// under a content-based dirty guard, which is the whole difference between the two designs.
//
// (b)(2) additionally pins the guard's KEYING: when the server's copy is a sanitized form and a
// mid-flight edit blocked adoption, the editor holds text the server has never seen. Recording the
// editor's live content as "saved" there would suppress the next boundary over genuinely unsaved
// words — silent data loss, exactly what the queued re-save failing exposes.
describe('ManualEditor — the debounce still saves when the queued mid-flight re-save fails (H9.4 a/b2)', () => {
  useAutosaveFailureFakeTimers()

  it('fires a save carrying the mid-flight edit when the queued re-save rejects non-transiently', async () => {
    await renderCreatedDocument()

    const firstSave = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSave.promise)
      .mockRejectedValue(new Error('network down'))

    await typeIntoEditor('hello')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // Edit #2 mid-flight: queues the re-save AND arms a fresh debounce deadline.
    await typeIntoEditor('hello world')
    await act(async () => {
      firstSave.resolve({ status: 'saved', version: 8, content: '<p>hello</p>' })
    })
    await flushMicrotasks()

    // The queued re-save (#2) fired with edit #2's content and REJECTED: the document is not clean,
    // and a generic Error is non-transient so no backoff retry is pending either.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      8,
    )
    expect(screen.getByTestId('me-save-error')).toHaveTextContent(SAVE_ERROR_MESSAGE)

    // The debounce armed by edit #2 is the last writer standing: crossing it must re-send edit #2.
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      8,
    )
  })

  it('still saves after a sanitizing response whose adoption a mid-flight edit blocked', async () => {
    await renderCreatedDocument()

    const firstSave = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSave.promise)
      .mockRejectedValue(new Error('network down'))

    await typeIntoEditor('hello')
    await crossDebounceBoundary()
    await typeIntoEditor('hello world')

    // The server answers save #1 with a SANITIZED form of what was sent. Adoption is skipped —
    // the editor no longer holds what was sent — so the editor keeps edit #2, which the server has
    // never received. Nothing here may be remembered as saved.
    await act(async () => {
      firstSave.resolve({ status: 'saved', version: 8, content: '<p>hello!</p>' })
    })
    await flushMicrotasks()
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>hello world</p>')

    // Queued re-save #2 rejects, so the boundary is again the only writer left, over content the
    // server has never stored.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      8,
    )
  })
})
