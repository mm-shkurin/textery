import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import { GENERIC_LOGIN_FAILURE_MESSAGE, NETWORK_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'
import * as api from '../../api/loginApi'
import { saveSession } from '../../utils/authSession'

// Two carried review CONCERNS on green commit 1b863fe, folded into the 5.6 indefinite-spinner RED
// step because both edit the same submit/catch path. Both mock `login` at the module boundary,
// like the sibling networkError test — a different seam from the indefinite-spinner file (which
// drives the real transport), so they live apart to keep each file's mocking strategy honest.
vi.mock('../../api/loginApi', () => ({ login: vi.fn() }))
vi.mock('../../utils/authSession', () => ({ saveSession: vi.fn() }))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'
const VALID_SESSION = {
  accessToken: 'access-tok',
  refreshToken: 'refresh-tok',
  accessTokenExpiresAt: '',
  refreshTokenExpiresAt: '',
}
const TRANSPORT_FAILURE = new TypeError('Failed to fetch')
const INVALID_CREDENTIALS = { errorCode: 'INVALID_CREDENTIALS', message: 'Неверный email или пароль' }

function fill() {
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
}

async function submit() {
  await act(async () => {
    fireEvent.click(screen.getByTestId('login-submit-button'))
  })
}

describe('LoginForm submit-path error handling', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
    vi.mocked(saveSession).mockReset()
  })

  // (1) NARROW-TRY / MISCLASSIFICATION — RED. login() SUCCEEDS; a POST-login step (saveSession)
  // throws a bare Error — a programming fault, the connection is fine. Today handleSubmit's `try`
  // wraps saveSession/navigate as well as login(), so this bare Error, having no `errorCode`, trips
  // the transport predicate `!hasProp(error,'errorCode')` in isLoginNetworkError and is shown as a
  // NETWORK failure ("check your connection") — blaming the network for a local bug. The
  // network/hang state must be reserved for login()'s OWN transport failures, not any bare Error
  // thrown anywhere inside the try. Green narrows the try to wrap only login() (or tightens the
  // predicate); this test fails against the current wide-try code.
  it('does not show the network-error state when a post-login step throws a bare Error', async () => {
    vi.mocked(api.login).mockResolvedValue(VALID_SESSION)
    vi.mocked(saveSession).mockImplementation(() => {
      throw new Error('cannot persist session')
    })
    fill()
    await submit()

    await waitFor(() => expect(screen.getByTestId('login-submit-button')).not.toBeDisabled())
    expect(screen.queryByTestId('login-network-error')).not.toBeInTheDocument()
    expect(document.body.textContent).not.toContain(NETWORK_LOGIN_FAILURE_MESSAGE)
    // (E) The user gets FEEDBACK, not a silent swallow: a post-login fault shows the generic
    // login-failure message on the form-error element (never the network banner). A green that
    // simply swallowed the throw — no banner AND no message — would pass the two lines above but
    // strand the user on a login page that did nothing; this pins that it does not.
    expect(screen.getByTestId('login-form-error')).toHaveTextContent(GENERIC_LOGIN_FAILURE_MESSAGE)
  })

  // (2) STALE-BANNER TWO-SUBMIT — born-green regression guard (PASSES on current code, which
  // already does setNetworkError(false) at submit entry). Nothing exercises a second submit today,
  // so a future reorder/early-return could strand the amber "check your connection" banner over a
  // working form with every existing test still green. This pins it: submit 1 = transport failure →
  // login-network-error shown; submit 2 = INVALID_CREDENTIALS → the banner is gone and the
  // field-level form-error is what remains.
  it('clears the stale network banner on the next submit', async () => {
    vi.mocked(api.login)
      .mockRejectedValueOnce(TRANSPORT_FAILURE)
      .mockRejectedValueOnce(INVALID_CREDENTIALS)
    fill()

    await submit()
    expect(await screen.findByTestId('login-network-error')).toHaveTextContent(
      NETWORK_LOGIN_FAILURE_MESSAGE,
    )

    await submit()
    await waitFor(() =>
      expect(screen.getByTestId('login-form-error').textContent).toBe(INVALID_CREDENTIALS.message),
    )
    expect(screen.queryByTestId('login-network-error')).not.toBeInTheDocument()
  })
})
