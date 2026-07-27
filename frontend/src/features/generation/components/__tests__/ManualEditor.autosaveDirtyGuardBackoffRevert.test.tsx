import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  RETRY_WINDOW_MS,
  crossDebounceBoundary,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  DIRTY_STATUS,
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

const SAVED_CONTENT = '<p>hello world</p>'
const SAVED_VERSION = 8

// Scenario H9.4, pre-condition (g) — the one window where the dirty guard is not reached at all.
//
// A pending transient-retry backoff deliberately keeps isSavingRef true, so an edit landing in that
// gap only QUEUES (saveAgainRequested) rather than launching a competing save — and save() returns
// from the queue branch BEFORE the guard. Undo the edit in that window and the queue is now aimed at
// content the server already holds: the backoff timer fires performSave over it, and that resolve
// sees the queued flag and chains a SECOND write. Two PUTs and two version bumps for a document
// nobody changed — the exact write amplification the guard exists to stop, arriving through the one
// door it does not watch.
//
// The guard therefore also gates the retry at FIRE time, where the queue question is finally
// answerable: nothing left to write means the in-flight cycle is simply over — settle clean, cancel
// the queue, write nothing. The stale debounce the revert armed then meets the ordinary guard in
// save() and is inert too.
describe('ManualEditor — reverting during a backoff wait writes nothing (H9.4 g)', () => {
  useAutosaveFailureFakeTimers()

  it('cancels the pending retry and its chained re-save when the editor is back to the saved content', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
      .mockRejectedValueOnce(new RequestTimeoutError())
      // Deliberately still armed: if the retry or its chained re-save ever fires, it resolves and
      // the call-count assertions below name exactly which one leaked.
      .mockResolvedValue({ status: 'saved', version: 9, content: SAVED_CONTENT })

    // Baseline save: the guard now remembers SAVED_CONTENT as confirmed by the server.
    await typeIntoEditor('hello world')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)

    // Edit #2 times out. Transient, so no banner and no give-up: a backoff timer is pending and the
    // save machinery stays "in flight" for its duration.
    await typeIntoEditor('hello world edited')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      '<p>hello world edited</p>',
      SAVED_VERSION,
    )
    expect(screen.queryByTestId('me-save-error')).toBeNull()

    // The undo lands INSIDE the backoff window, so it can only queue — save() never reaches the
    // guard from here.
    await typeIntoEditor('hello world')
    expect(dispatchBeforeUnload()).toBe(true)

    // Let the whole backoff schedule and the stale debounce both play out.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()

    // Neither the retry nor a chained re-save wrote anything: the server already holds this text.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // The abandoned retry must not leave the document stuck mid-save either — it is genuinely clean.
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()
    expect(screen.queryByTestId('me-save-error')).toBeNull()
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
