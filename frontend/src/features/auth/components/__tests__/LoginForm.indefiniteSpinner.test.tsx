import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import { NETWORK_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

// Spec 5.6 (02_UI_Tests.md:169): "a retry-capable network-error state is shown, NOT an indefinite
// spinner." The network-REJECTION half is covered in LoginForm.networkError.test.tsx. This file
// owns the HANG: if `login()`'s underlying fetch never settles (a proxy black-holes the POST, a
// dropped SYN), handleSubmit's `catch`/`finally` never run, so `isSubmitting` stays true FOREVER —
// the spinner spins, the button never re-enables, no retry short of a page reload. There is no
// AbortController and no fetch timeout in `frontend/src` today (httpClient awaits a bare `fetch`).
//
// This file DELIBERATELY does NOT mock loginApi. The green fix is an AbortController/setTimeout in
// the SHARED httpClient, so the test must drive the REAL login → postJson → httpClient chain; the
// timeout there is what turns the hang into an abort-rejection that the form's existing
// transport-shaped `login-network-error` branch already handles. Mocking `login` with a
// never-settling promise would bypass httpClient and could never go green against a fix living
// there. So the seam mocked is the transport (global `fetch`), one layer below httpClient.
//
// Fake timers: the green fix schedules the abort on a timer, so the test advances fake time past
// the (bounded) client-side timeout. advanceTimersByTimeAsync also flushes the microtasks the
// abort → reject → setState cascade needs.

// The black-holed request: fetch's promise stays pending forever.
const NEVER_SETTLES = (): Promise<Response> => new Promise<Response>(() => {})

describe('LoginForm indefinite-spinner / hung request', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn(NEVER_SETTLES))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('converts a hung request into the retry-capable network-error state, not an endless spinner', async () => {
    renderWithRouter(<LoginForm />)
    fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
    fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })

    await act(async () => {
      fireEvent.click(screen.getByTestId('login-submit-button'))
    })
    // Request is in flight: the spinner is up and the button is disabled — the pre-timeout state.
    expect(screen.getByTestId('login-submit-button')).toBeDisabled()

    // Advance well past any bounded client-side timeout the httpClient fix installs. On CURRENT
    // code no timer is scheduled, so the fetch stays pending and nothing below renders — RED.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })

    // The hang must have become the SAME retry-capable network-error state a transport rejection
    // yields: a distinct element, announced to AT, no lingering spinner, and the submit affordance
    // re-enabled so the user can actually retry.
    const networkError = screen.queryByTestId('login-network-error')
    expect(networkError).toBeInTheDocument()
    expect(networkError).toHaveAttribute('role', 'alert')
    expect(networkError).toHaveTextContent(NETWORK_LOGIN_FAILURE_MESSAGE)
    expect(screen.queryByTestId('login-loading-indicator')).not.toBeInTheDocument()
    expect(screen.getByTestId('login-submit-button')).not.toBeDisabled()
  })
})
