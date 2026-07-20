import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

// Spec 5.4 lockout contract (DESIGN DECISION 2026-07-20, user-confirmed): the backend rejects a
// locked-out login with error_code ACCOUNT_LOCKED and an HTTP Retry-After header (seconds), which
// loginApi surfaces as `retryAfterSeconds` on the rejection. At the COMPONENT layer that header is
// MOCKED — reading the real header is the deferred red-frontend-api step, so this test must not
// touch loginApi/httpClient. `message` is deliberately '' (per the round-8 premortem seam note):
// the locked-screen COPY lives in the form, never in the api mapper, so this fixture supplies NO
// lockout text and the test proves the form authors its own.
// 292s → 04:52, matching the mockup (04-account-locked.html).
const RETRY_AFTER_SECONDS = 292
const ACCOUNT_LOCKED_ERROR = {
  errorCode: 'ACCOUNT_LOCKED',
  message: '',
  retryAfterSeconds: RETRY_AFTER_SECONDS,
}

// Awaiting an async `act` flushes the rejected-login microtask (and the catch's setState) even
// under fake timers, since the microtask queue is not faked — cleaner than findBy, which would
// have to advance the fake clock to time out.
async function renderRejectAndSubmit() {
  vi.mocked(api.login).mockRejectedValue(ACCOUNT_LOCKED_ERROR)
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  await act(async () => {
    fireEvent.click(screen.getByTestId('login-submit-button'))
  })
}

// RED 2026-07-20 (scenario 5.4): LoginForm has NO ACCOUNT_LOCKED branch and no locked screen — on
// this rejection it currently renders GENERIC_LOGIN_FAILURE_MESSAGE ("Не удалось войти") inline in
// login-form-error and keeps the login form. All four cases fail with TestingLibraryElementError:
// "Unable to find an element by: [data-testid='account-locked-screen' | 'account-locked-countdown' |
// 'account-locked-back-to-login']". Un-skip in green-frontend.
describe.skip('LoginForm account-locked screen', () => {
  // Fixed system clock: the countdown is a live timer derived from a deadline, so asserting its
  // text against real wall-clock time is a race. Fake timers pin "now" so the initial render value
  // is deterministic and advancing by exactly 1s is the only thing that moves it.
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-20T00:00:00.000Z'))
  })

  afterEach(() => {
    vi.mocked(api.login).mockReset()
    vi.useRealTimers()
  })

  // The locked screen REPLACES the login form: the normal submit affordance must be gone, so a
  // locked-out user cannot keep hammering the endpoint. Both directions are asserted — the new
  // screen present, the old form absent — because either alone would pass a half-built state.
  it('replaces the login form with the account-locked screen on an ACCOUNT_LOCKED rejection', async () => {
    await renderRejectAndSubmit()

    expect(screen.getByTestId('account-locked-screen')).toBeInTheDocument()
    expect(screen.queryByTestId('login-submit-button')).not.toBeInTheDocument()
  })

  // The countdown's initial value is DERIVED from retryAfterSeconds, formatted MM:SS: 292 → 04:52,
  // exactly the mockup. Exact `.textContent` toBe (NOT toHaveTextContent, which is a jest-dom
  // substring match that would also pass "04:521" or a labelled "осталось 04:52") so a wrong
  // derivation — seconds shown raw, minutes miscomputed, an off-by-one on the ceil, or extra
  // glyphs bleeding into the timer element — fails loudly. Matches the siblings' textContent.toBe
  // house style.
  it('shows the initial retry countdown as MM:SS derived from retryAfterSeconds', async () => {
    await renderRejectAndSubmit()

    expect(screen.getByTestId('account-locked-countdown').textContent).toBe('04:52')
  })

  // "with the retry countdown" (spec) means it COUNTS: a frozen 04:52 would satisfy the assertion
  // above forever. Advancing exactly one second must move it to 04:51 — proof the clock runs.
  it('ticks the countdown down by one second', async () => {
    await renderRejectAndSubmit()
    expect(screen.getByTestId('account-locked-countdown').textContent).toBe('04:52')

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    expect(screen.getByTestId('account-locked-countdown').textContent).toBe('04:51')
  })

  // A back-to-login control returns the user to the login form. Asserted by the form's submit
  // button reappearing (and the locked screen going away), which is the reachable in-app path back
  // — the deferred selenium (6.5) closes the full navigation leg.
  it('returns to the login form when the back-to-login control is used', async () => {
    await renderRejectAndSubmit()

    await act(async () => {
      fireEvent.click(screen.getByTestId('account-locked-back-to-login'))
    })

    expect(screen.getByTestId('login-submit-button')).toBeInTheDocument()
    expect(screen.queryByTestId('account-locked-screen')).not.toBeInTheDocument()
  })
})
