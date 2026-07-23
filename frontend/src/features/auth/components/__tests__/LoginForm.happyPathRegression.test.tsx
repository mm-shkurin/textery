import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'
import type { LoginResult } from '../../api/loginApi'
import { saveSession } from '../../utils/authSession'

// Scenario 6.1 — regression guard. The OAuth work (VK/Yandex buttons, the OAuthErrorBanner reading
// location.state.oauthError, the /auth/callback route) was ADDITIVE; this pins that the classic
// email+password happy path through LoginForm is unchanged: valid creds → saveSession → navigate to
// the app-shell default ('/', {replace:true}) — and that the OAuth additions are INERT on this path
// (no oauthError state, so no oauth banner; no rejection, so no form-error). Born-green.
//
// Seams: useNavigate (the landing side effect, asserted for exact args), loginApi.login (the
// transport), and authSession.saveSession (the persistence gate). safeRedirectTarget is left REAL —
// with no location.state.from it must resolve to the app-shell default '/'.
const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../api/loginApi', () => ({ login: vi.fn() }))
vi.mock('../../utils/authSession', () => ({ saveSession: vi.fn() }))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'
const SESSION: LoginResult = {
  accessToken: 'access-tok',
  refreshToken: 'refresh-tok',
  accessTokenExpiresAt: '2026-07-16T18:15:00+00:00',
  refreshTokenExpiresAt: '2026-07-23T18:00:00+00:00',
}

function fillAndRender() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginForm />
    </MemoryRouter>,
  )
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
}

async function submit() {
  await act(async () => {
    fireEvent.click(screen.getByTestId('login-submit-button'))
  })
}

describe('LoginForm email+password happy path (OAuth-additions regression guard)', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
    vi.mocked(saveSession).mockReset()
    navigate.mockReset()
  })

  it('signs in with valid credentials and lands on the app-shell default, OAuth additions inert', async () => {
    vi.mocked(api.login).mockResolvedValue(SESSION)
    vi.mocked(saveSession).mockReturnValue(true)
    fillAndRender()

    await submit()

    await waitFor(() =>
      expect(screen.getByTestId('login-submit-button')).not.toBeDisabled(),
    )
    expect(api.login).toHaveBeenCalledTimes(1)
    expect(api.login).toHaveBeenCalledWith(EMAIL, PASSWORD)
    expect(saveSession).toHaveBeenCalledTimes(1)
    expect(saveSession).toHaveBeenCalledWith(SESSION)
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    // OAuth additions are inert on the classic path: no location.state.oauthError → no banner,
    // and a successful login → no field-validation error.
    expect(screen.queryByTestId('login-oauth-error')).not.toBeInTheDocument()
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })
})
