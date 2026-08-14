import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { clearSession, getAccessToken, saveSession } from '../../auth/utils/authSession'

// UI scenario 4 — a `GET /me` that fails does NOT end the session.
//
// Nothing is mocked below the transport on purpose. The property under test lives in the seam
// between `identityRequest` and `authorizedRequest`: the latter answers a 401 by renewing and
// `performRenewal` calls `clearSession()` on ANY renewal failure. That is right for a request the
// user made and catastrophic for this one, which after story 13 fires unprompted on every
// authenticated page — one blip during a rolling deploy would sign out every open tab and take
// the editor's unsaved text with it. Mocking the profile client would assert nothing about that.
describe('a failing GET /me', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    resetIdentity()
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
    resetIdentity()
  })

  it('keeps the session, stays on the screen, and leaves «Выйти» working', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: async () => ({ error_code: 'INTERNAL', message: 'boom' }),
    })

    renderWithRouter(<ProfilePage />)

    // The screen ENDS in a message with «Повторить» — never a spinner that keeps turning, which
    // is indistinguishable from a hung tab.
    expect(await screen.findByTestId('profile-load-failed')).toBeInTheDocument()
    expect(screen.getByTestId('profile-load-retry')).toBeInTheDocument()

    // The session survived the failure, and the user was not thrown at the login screen.
    expect(getAccessToken()).toBe('access-token')
    expect(screen.getByTestId('profile-screen')).toBeInTheDocument()
    expect(screen.queryByTestId('login-form')).not.toBeInTheDocument()
    // A 500 is not a 401: no renewal was attempted, so there is exactly one request.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/me')

    // The degraded header is visibly a FAILURE, not a loading placeholder and not a healthy
    // account with no name.
    expect(screen.getAllByTestId('profile-avatar-failed').length).toBeGreaterThan(0)

    // And the way out still works. Gating the menu's contents on a successful /me would lock the
    // user inside a session they cannot end, on the exact failure they most want to leave.
    fireEvent.click(screen.getByTestId('profile-profile-button'))
    fireEvent.click(screen.getByTestId('profile-logout-button'))

    await waitFor(() => expect(getAccessToken()).toBeNull())
  })
})
