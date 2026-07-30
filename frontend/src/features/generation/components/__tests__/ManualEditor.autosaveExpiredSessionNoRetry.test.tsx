import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import * as documentApi from '../../api/documentApi'
import {
  RETRY_WINDOW_MS,
  flushMicrotasks,
  typeAndFireAutosave,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import { renderCreatedDocument } from './ManualEditor.autosaveRender.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.3: not every autosave failure is transient, and the per-kind handling must NOT treat
// an expired session as something a backoff can heal. Retrying a signed-out request only burns the
// backoff schedule against a request that cannot succeed until the user re-authenticates. So an
// expired session skips the retry loop entirely and surfaces the re-auth prompt immediately.
//
// This is a characterization GUARD, not a red→green cycle: today no autosave failure retries at all,
// so a session failure is already fired exactly once. It passes now and guards the H9.3 retry work
// (autosaveRetryBackoff) from mistakenly folding SessionExpiredError into the transient-retry arm.

describe('ManualEditor — an expired-session autosave prompts re-auth and is never retried (H9.3)', () => {
  useAutosaveFailureFakeTimers()

  it('fires the autosave once, does not retry across the backoff window, and shows the re-auth message', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockRejectedValue(new SessionExpiredError())

    await typeAndFireAutosave('hello world')

    // The re-auth prompt is shown on the first failure — no waiting on a backoff.
    expect(screen.getByTestId('me-save-error')).toHaveTextContent('Сессия истекла. Войдите снова.')

    // Advancing well past any backoff schedule fires NO retry: a signed-out request cannot recover.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
  })
})
