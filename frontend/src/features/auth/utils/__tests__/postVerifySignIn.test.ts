import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { signInAfterVerification } from '../postVerifySignIn'
import { forgetRegistration, rememberRegistration } from '../registrationHandoff'
import { clearSession, getAccessToken } from '../authSession'
import * as loginApi from '../../api/loginApi'

vi.mock('../../api/loginApi')

const EMAIL = 'user@example.ru'
const PASSWORD = 'Str0ng!Pass'

function tokens() {
  return {
    accessToken: 'access-1',
    refreshToken: 'refresh-1',
    accessTokenExpiresAt: '2026-07-17T09:00:00Z',
    refreshTokenExpiresAt: '2026-07-24T08:00:00Z',
  }
}

describe('signInAfterVerification', () => {
  beforeEach(() => {
    rememberRegistration(EMAIL, PASSWORD)
  })

  afterEach(() => {
    forgetRegistration()
    clearSession()
    vi.resetAllMocks()
  })

  it('signs the user in with the remembered password and sends them to the landing', async () => {
    vi.mocked(loginApi.login).mockResolvedValue(tokens())

    const destination = await signInAfterVerification(EMAIL)

    expect(loginApi.login).toHaveBeenCalledWith(EMAIL, PASSWORD)
    expect(destination).toBe('/')
    expect(getAccessToken()).toBe('access-1')
  })

  // The reload case, and the reason the handoff is in memory: losing it is the correct
  // outcome of a refresh, so the screen must have somewhere to send them.
  it('sends the user to sign in by hand when no password was handed over', async () => {
    forgetRegistration()

    const destination = await signInAfterVerification(EMAIL)

    expect(destination).toBe('/login')
    expect(loginApi.login).not.toHaveBeenCalled()
  })

  // The account IS verified — that already succeeded and a failed convenience login does not
  // undo it. Losing the shortcut is not a failure of the thing that worked.
  it('sends the user to sign in by hand when the login call fails', async () => {
    vi.mocked(loginApi.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS' })

    const destination = await signInAfterVerification(EMAIL)

    expect(destination).toBe('/login')
    expect(getAccessToken()).toBeNull()
  })

  // A 200 carrying no token is a broken contract, not a sign-in. Landing them "authenticated"
  // with nothing to send would fail at the first request, somewhere that cannot explain itself.
  it('refuses to treat a tokenless success as a session', async () => {
    vi.mocked(loginApi.login).mockResolvedValue({ ...tokens(), accessToken: '' })

    const destination = await signInAfterVerification(EMAIL)

    expect(destination).toBe('/login')
    expect(getAccessToken()).toBeNull()
  })

  it('does not reuse the password for a second verification', async () => {
    vi.mocked(loginApi.login).mockResolvedValue(tokens())
    await signInAfterVerification(EMAIL)
    vi.mocked(loginApi.login).mockClear()

    const destination = await signInAfterVerification(EMAIL)

    expect(destination).toBe('/login')
    expect(loginApi.login).not.toHaveBeenCalled()
  })
})
