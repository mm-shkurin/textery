import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import type { HttpError } from '../../../../shared/api/httpClient'
import { isTransientFailure } from '../../utils/autosaveRetryPolicy'
import * as documentApi from '../../api/documentApi'
import {
  crossDebounceBoundary,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'
import {
  REVISED_CONTENT,
  REVISED_PLAIN,
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
  echoSavedAtRetryVersion,
  playOutRetrySchedule,
  saveBaselineThenTransientFailure,
} from './ManualEditor.autosaveFixture'
import {
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// A DEFINITE server rejection: the server answered, and its answer is that the write did not apply.
// That is what licenses the fire-time suppression below — the remembered content is still provably
// what the server holds, so there is nothing to write. Deliberately NOT a RequestTimeoutError: that
// is a purely client-side deadline (httpClient's timer rejects whether or not the transport ever
// aborted), so a timed-out PUT may well have been committed and the memory is no longer trustworthy.
// The timeout case is the inverse assertion and lives in its own sibling suite — see
// ManualEditor.autosaveDirtyGuardTimeoutRevert.test.tsx.
//
// Typed as HttpError, not left as a bare object literal: isTransientFailure narrows through
// isHttpError, so a fixture that quietly stopped satisfying that shape would schedule NO retry —
// and this suite, which asserts that nothing further is written, would keep passing for entirely
// the wrong reason. The premise is re-checked as an assertion inside the test too.
const DEFINITE_SERVER_REJECTION: HttpError = { status: 503, body: {} }

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
//
// Scope: this holds only for a failure that PROVABLY did not reach the server. See the fixture note
// on DEFINITE_SERVER_REJECTION above and the opposite-direction timeout sibling.
describe('ManualEditor — reverting during a backoff wait writes nothing (H9.4 g)', () => {
  useAutosaveFailureFakeTimers()

  it('cancels the pending retry and its chained re-save when the editor is back to the saved content', async () => {
    // The whole scenario presupposes a backoff is scheduled at all. Pinned, not assumed.
    expect(isTransientFailure(DEFINITE_SERVER_REJECTION)).toBe(true)

    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
      .mockRejectedValueOnce(DEFINITE_SERVER_REJECTION)
      // Deliberately still armed: if the retry or its chained re-save ever fires, it resolves and
      // the call-count assertions below name exactly which one leaked.
      .mockImplementation(echoSavedAtRetryVersion)

    // Baseline save (the guard now remembers SAVED_CONTENT as confirmed by the server), then edit #2
    // which the server REFUSES with a 503. Transient, so no banner and no give-up: a backoff timer
    // is pending and the save machinery stays "in flight" for its duration. Crucially the server
    // told us it did NOT apply the write, so SAVED_CONTENT is still what it holds.
    await saveBaselineThenTransientFailure()

    // The undo lands INSIDE the backoff window, so it can only queue — save() never reaches the
    // guard from here.
    await typeIntoEditor(SAVED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)

    await playOutRetrySchedule()

    // Neither the retry nor a chained re-save wrote anything: the server already holds this text.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // The abandoned retry must not leave the document stuck mid-save either — it is genuinely clean.
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
    expect(dispatchBeforeUnload()).toBe(false)

    // ...and the suppression was CONDITIONAL on the content, not a blanket "a retry never writes".
    // Deleting the fire-time question outright and always settling clean satisfies every assertion
    // above — real unsaved retries silently dropped — and dies here. The re-arm below also gives
    // the `false` three lines up something to mean: ManualEditor registers the beforeunload listener
    // only while dirty, so `false` alone is equally the answer when no guard was ever installed.
    await typeIntoEditor(REVISED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    // Still SAVED_VERSION: the abandoned retry wrote nothing, so it bumped nothing.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      REVISED_CONTENT,
      SAVED_VERSION,
    )
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
