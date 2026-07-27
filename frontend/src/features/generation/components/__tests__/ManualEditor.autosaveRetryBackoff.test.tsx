import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import { MAX_AUTOSAVE_ATTEMPTS, SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  RETRY_WINDOW_MS,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import { SAVED_STATUS } from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// The bounded retry contract this scenario pins: the failed autosave fires once, then re-fires on a
// capped backoff schedule up to a fixed ceiling before giving up and surfacing the banner. The exact
// total (initial attempt + retries) is the production constant MAX_AUTOSAVE_ATTEMPTS, imported so the
// contract lives in one place — RETRY_WINDOW_MS is sized so the whole schedule plays out inside it,
// making the count deterministic, not a range.

// Scenario H9.3 (autosave failures handled per kind). A TRANSIENT autosave failure — a request
// timeout or a 5xx — is the one failure kind where retrying can actually recover. This suite pins
// the retry contract: the failed autosave re-fires ITSELF on a backoff timer (no fresh edit and no
// Сохранить click needed), the backoff is scheduled rather than an immediate hammer, and the retry
// loop is BOUNDED so a server that stays down does not spin forever. A big generous timer advance
// (RETRY_WINDOW_MS) stands in for "however long the capped backoff schedule needs" so the assertions
// do not hardcode green's exact per-attempt delays.

describe('ManualEditor — a transient autosave failure retries on a capped backoff (H9.3)', () => {
  useAutosaveFailureFakeTimers()

  it('re-fires a timed-out autosave on a backoff timer (not immediately) and clears the failure once it succeeds', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockRejectedValueOnce(new RequestTimeoutError())
      .mockResolvedValue({ status: 'saved', version: 8, content: '<p>hello world</p>' })

    await typeAndFireAutosave('hello world')

    // The first autosave fired and rejected with a timeout — exact content and version (a failed
    // save does not bump the version, so the retry re-sends the same 7).
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(1, 'doc-1', '<p>hello world</p>', 7)

    // The retry is SCHEDULED on a timer, not fired synchronously in the reject handler — draining
    // only the microtask queue must not have produced a second attempt yet.
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // Crossing the backoff window re-fires the SAME autosave with no new edit and no click.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // The retry re-sends the identical content at the same version — not stale, not re-serialized wrong.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', '<p>hello world</p>', 7)
    // The recovered save settles clean: the failure banner is gone and the saved status shows.
    expect(screen.queryByTestId('me-save-error')).toBeNull()
    expect(screen.getByText(SAVED_STATUS).textContent).toBe(SAVED_STATUS)
  })

  it('stops retrying a persistently-failing transient autosave after a bounded number of attempts and shows the failure', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockRejectedValue({ status: 503, body: {} })

    await typeAndFireAutosave('hello world')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // Let the whole capped-backoff schedule play out. It retries automatically and gives up after
    // exactly MAX_AUTOSAVE_ATTEMPTS total attempts (initial + capped retries) — the window is sized
    // so the whole schedule fits inside it, so the count is exact, not "more than one".
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(MAX_AUTOSAVE_ATTEMPTS)

    // The loop is BOUNDED: a further, equally long wait produces no additional attempts — the count
    // holds at the same defined ceiling, not merely "unchanged from whatever ran".
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(MAX_AUTOSAVE_ATTEMPTS)

    // Having given up, it surfaces the failed-save banner.
    expect(screen.getByTestId('me-save-error')).toHaveTextContent(SAVE_ERROR_MESSAGE)
  })

  // Premortem gap (H9.3): an edit typed during the backoff WAIT must not be silently lost. If the
  // retry re-sent the stale content captured at the failed attempt, the successful retry would mark
  // the doc "Сохранено" over text that was never sent — data loss with no banner. The retry must
  // re-serialize the editor's LATEST content at fire time.
  it('re-sends the latest content typed during the backoff wait, not the stale content from the failed attempt', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockRejectedValueOnce(new RequestTimeoutError())
      .mockResolvedValue({ status: 'saved', version: 8, content: '<p>updated during wait</p>' })

    await typeAndFireAutosave('stale content')
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(1, 'doc-1', '<p>stale content</p>', 7)

    // While the backoff timer is pending, the user keeps typing — this is the gap the retry must not
    // drop. The edit lands with no save in flight to queue against; only re-serialization saves it.
    await typeIntoEditor('updated during wait')

    // The retry fires across the window and must carry the LATEST content, at the unchanged version.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()

    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', '<p>updated during wait</p>', 7)
    // Clean only over content that was actually sent — never marked saved over the lost keystrokes.
    expect(screen.queryByTestId('me-save-error')).toBeNull()
    expect(screen.getByText(SAVED_STATUS).textContent).toBe(SAVED_STATUS)
  })
})
