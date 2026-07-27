import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import * as documentApi from '../../api/documentApi'
import { AUTOSAVE_DEBOUNCE_MS, RETRY_WINDOW_MS, flushMicrotasks } from './ManualEditor.autosave.testSupport'

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
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('fires the autosave once, does not retry across the backoff window, and shows the re-auth message', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
    await flushMicrotasks()

    vi.mocked(documentApi.saveDocument).mockRejectedValue(new SessionExpiredError())

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    await act(async () => {
      fireEvent.input(contentArea)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    await flushMicrotasks()

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
