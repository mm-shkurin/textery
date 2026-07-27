import { describe, expect, it, vi } from 'vitest'
import { act } from '@testing-library/react'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  RETRY_WINDOW_MS,
  defer,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.3, gap (a) — the queued-edit-dropped-on-failure hole confirmed by the E3.2 premortem.
// The save state machine serializes saves: an edit landing while a save is in flight only sets
// `saveAgainRequested`, to be re-fired from the in-flight save's RESOLVE handler. But the REJECT
// handler resets `saveAgainRequested = false` (useDocumentSave.ts) and does nothing else, so if the
// in-flight save fails the queued newer edit is silently dropped — autosave only re-arms on a fresh
// edit, so a user who stops typing loses that keystroke burst with no banner and no retry.
//
// The transient-retry work must not have this hole: after a failed save that had a queued edit, the
// LATEST (queued) content must be re-sent, not abandoned.

describe('ManualEditor — a queued edit is not lost when the in-flight autosave fails (H9.3 gap a)', () => {
  useAutosaveFailureFakeTimers()

  it('re-fires the queued latest edit after the in-flight autosave rejects, instead of dropping it', async () => {
    await renderCreatedDocument()

    const saveA = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(saveA.promise)
      .mockResolvedValue({ status: 'saved', version: 8, content: '<p>second version</p>' })

    // Edit #1 → debounce → autosave A fires and stays in flight.
    await typeAndFireAutosave('first version')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      '<p>first version</p>',
      CREATED_VERSION,
    )

    // Edit #2 lands while A is in flight: it queues a re-save rather than launching a second call.
    await typeAndFireAutosave('second version')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // A fails transiently. The queued edit must survive: after the backoff the LATEST content is
    // re-sent. Today the reject handler drops the queued flag, so no second call ever fires.
    await act(async () => {
      saveA.reject(new RequestTimeoutError())
    })
    await flushMicrotasks()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      '<p>second version</p>',
      CREATED_VERSION,
    )
  })
})
