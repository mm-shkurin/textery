import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import { SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  RETRY_WINDOW_MS,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// The bounded retry contract this scenario pins: the failed autosave fires once, then re-fires on a
// capped backoff schedule up to a fixed ceiling before giving up and surfacing the banner. The exact
// total (initial attempt + retries) is a value the test DEFINES — RETRY_WINDOW_MS is sized so the
// whole schedule plays out inside it, so the count is deterministic, not a range. Green must cap at
// exactly this many attempts.
const MAX_AUTOSAVE_ATTEMPTS = 4

// Scenario H9.3 (autosave failures handled per kind). A TRANSIENT autosave failure — a request
// timeout or a 5xx — is the one failure kind where retrying can actually recover. This suite pins
// the retry contract: the failed autosave re-fires ITSELF on a backoff timer (no fresh edit and no
// Сохранить click needed), the backoff is scheduled rather than an immediate hammer, and the retry
// loop is BOUNDED so a server that stays down does not spin forever. A big generous timer advance
// (RETRY_WINDOW_MS) stands in for "however long the capped backoff schedule needs" so the assertions
// do not hardcode green's exact per-attempt delays.

describe('ManualEditor — a transient autosave failure retries on a capped backoff (H9.3)', () => {
  useAutosaveFakeTimers()

  // RED (H9.3): no retry exists — saveDocument fires once and stays there.
  // AssertionError: expected "vi.fn()" to be called 2 times, but got 1 times.
  it.skip('re-fires a timed-out autosave on a backoff timer (not immediately) and clears the failure once it succeeds', async () => {
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
    expect(screen.getByText('Сохранено').textContent).toBe('Сохранено')
  })

  // RED (H9.3): no retry exists — only one attempt ever fires.
  // AssertionError: expected 1 to be 4.
  it.skip('stops retrying a persistently-failing transient autosave after a bounded number of attempts and shows the failure', async () => {
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
})
