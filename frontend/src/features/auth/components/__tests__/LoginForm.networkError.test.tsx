import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'
import * as api from '../../api/loginApi'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

// Spec 5.6 (02_UI_Tests.md:169): a request that fails due to a NETWORK error or TIMEOUT — not a
// validation/business response — must render a distinct, retry-capable network-error state,
// visually distinct from a field-level validation error, and NOT an indefinite spinner. The
// distinction is made ON WHAT THE REJECTION IS, not on copy:
//   * a bodyless transport failure rejects with a bare TypeError (fetch's own "Failed to fetch") —
//     no errorCode, no body: the canonical "connection dropped" case.
//   * a gateway/proxy 502 (deploy rolling, upstream down) reaches loginApi as an unparseable body
//     → { errorCode: 'UNKNOWN_ERROR', message: '', status: 5xx }. It is a TRANSPORT-class failure
//     wearing a codeless UNKNOWN_ERROR, told apart from a genuine codeless BUSINESS error only by
//     its 5xx status (round-8 premortem CREDIBLE (1), carried onto 5.6). The COMPONENT layer mocks
//     the api, so these fixtures stand in for what loginApi surfaces; the api preserving `status`
//     is the sibling red-frontend-api step this file's (c) makes user-visible.
// Copy lives in the FORM, never the api mapper (round-8 display seam): fixtures carry no network
// text, so the assertions can only pass on form-owned copy. Network copy is asserted DISTINCT from
// the validation constant rather than pinned verbatim (green owns the exact words; align-design
// pins them against the mockup).
const TRANSPORT_FAILURE = new TypeError('Failed to fetch')
const GATEWAY_502 = { errorCode: 'UNKNOWN_ERROR', message: '', status: 502 }
const CODELESS_BUSINESS_400 = { errorCode: 'UNKNOWN_ERROR', message: '', status: 400 }
// Status-ABSENT codeless business error — the shape a real codeless business error has IN PRODUCTION
// today, where the api layer drops `status` (green-frontend-api threads it through later). The (d)
// fixture bakes in status:400 and so cannot catch a `status===undefined → network` slip; this one
// pins that a status-less rejection carrying an errorCode STAYS on login-form-error.
const CODELESS_BUSINESS_NO_STATUS = { errorCode: 'UNKNOWN_ERROR', message: '' }
const INVALID_CREDENTIALS = { errorCode: 'INVALID_CREDENTIALS', message: 'Неверный email или пароль' }
// The backend's app-wide 500 shape: a codeful two-field { error_code:'INTERNAL_ERROR', message }
// with NO status (toAuthApiError drops status on the coded path). A SERVER fault, retry-affording.
const INTERNAL_ERROR_500 = { errorCode: 'INTERNAL_ERROR', message: 'oops' }

async function submitRejectingWith(rejection: unknown) {
  vi.mocked(api.login).mockRejectedValue(rejection)
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  await act(async () => {
    fireEvent.click(screen.getByTestId('login-submit-button'))
  })
}

describe('LoginForm network/transport error', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  // (a) THE CANONICAL NETWORK CASE — a bodyless transport failure. Today this collapses to the
  // generic login-failure message in `login-form-error` (loginErrorMessage's final fallback),
  // indistinguishable from a wrong-password validation error. 5.6 requires a DISTINCT element:
  // `login-network-error` present, `login-form-error` absent. role="alert" so a screen-reader user
  // is told (same class as 5.3's finding). Retry-capable = the submit affordance re-enables so the
  // user can resubmit; the finite-rejection path must NOT leave the spinner running.
  it('shows the distinct retry-capable network-error state on a bodyless transport failure', async () => {
    await submitRejectingWith(TRANSPORT_FAILURE)

    const networkError = await screen.findByTestId('login-network-error')
    expect(networkError).toHaveAttribute('role', 'alert')
    expect(networkError.textContent?.trim()).not.toBe('')
    expect(networkError.textContent).not.toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
    expect(screen.queryByTestId('login-loading-indicator')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('login-submit-button')).not.toBeDisabled())
    // Non-disclosure carried from nonContractError test 1 (deleted; the TypeError case lives here
    // now): fetch's raw transport text never reaches the screen.
    expect(document.body.textContent).not.toContain('Failed to fetch')
  })

  // (b) VISUAL DISTINCTION, validation half — a field/credentials error stays in `login-form-error`
  // and must NOT be swept into the network state. Born-green (pins current correct routing so green
  // cannot collapse the two states into one element).
  it('keeps a validation error in the form-error element, not the network-error state', async () => {
    await submitRejectingWith(INVALID_CREDENTIALS)

    await waitFor(() =>
      expect(screen.getByTestId('login-form-error').textContent).toBe(INVALID_CREDENTIALS.message),
    )
    expect(screen.queryByTestId('login-network-error')).not.toBeInTheDocument()
  })

  // (c) THE GATEWAY 502 — the operationally-common trigger (a deploy 502s for 90s). It is a
  // transport-class failure and must reach the SAME network-error state as (a), told from a
  // business error by its 5xx status. Today it falls to the generic form-error message — the exact
  // incident CREDIBLE (1) describes ("locked out during the deploy"). RED until green branches the
  // network state on a 5xx status (fed in production by the red-frontend-api `status` pass-through).
  it('shows the network-error state on a gateway 5xx with an unparseable body', async () => {
    await submitRejectingWith(GATEWAY_502)

    // Same accessible network-error state as (a): assert the role binding too, not just element
    // presence — a div carrying the testid but no role="alert" would be a different (silent-to-AT)
    // state that must not pass as "reached the network-error state".
    const networkError = await screen.findByTestId('login-network-error')
    expect(networkError).toHaveAttribute('role', 'alert')
    expect(networkError.textContent).not.toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  // (d) THE CONVERSE GUARD — a codeless BUSINESS error (truthy body, no error_code, 4xx status) is
  // NOT a network failure: it stays in `login-form-error`. Born-green; pins the discriminator to
  // "5xx status", so green cannot lazily route every UNKNOWN_ERROR to the network state and strand
  // a real client-side 4xx behind a "check your connection" message.
  it('keeps a codeless 4xx business error in the form-error element', async () => {
    await submitRejectingWith(CODELESS_BUSINESS_400)

    await waitFor(() =>
      expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE),
    )
    expect(screen.queryByTestId('login-network-error')).not.toBeInTheDocument()
  })

  // (f) RED (Task 6) — THE CODEFUL SERVER 500. A login 500 arrives as the app-wide codeful
  // { errorCode:'INTERNAL_ERROR', message } with NO status. It is a SERVER fault and must reach the
  // SAME retry-capable network-error state as (a)/(c), NOT the field-level form-error. Today
  // isLoginNetworkError sees an errorCode + no status → false, so applyLoginFailure routes it to
  // setFormError and it lands in login-form-error. RED until green adds the INTERNAL_ERROR sentinel
  // branch. Skipped until then.
  it.skip('shows the network-error state on a codeful INTERNAL_ERROR 500', async () => {
    await submitRejectingWith(INTERNAL_ERROR_500)

    const networkError = await screen.findByTestId('login-network-error')
    expect(networkError).toHaveAttribute('role', 'alert')
    expect(networkError.textContent).not.toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  // (e) THE STATUS-ABSENT CONVERSE — pins the discriminator to `status >= 500` ONLY, never
  // `status === undefined || status >= 500`. A codeless business error arrives status-less in
  // production (the api drops status); it must STAY in login-form-error, not leak to the network
  // state behind a "check your connection" message. (d) can't catch this — it bakes in status:400.
  it('keeps a status-less codeless business error in the form-error element', async () => {
    await submitRejectingWith(CODELESS_BUSINESS_NO_STATUS)

    await waitFor(() =>
      expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE),
    )
    expect(screen.queryByTestId('login-network-error')).not.toBeInTheDocument()
  })
})
