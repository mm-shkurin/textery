import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfileMenu } from '../../../shared/components/profile/ProfileMenu'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { clearSession, saveSession } from '../../auth/utils/authSession'

// UI scenario 5 — one identity per PAGE, not one per component.
//
// The account menu is mounted more than once at a time, and `/me` is what this story makes the
// product's highest-rate endpoint. A hook that fetched on mount would multiply that by the number
// of mounts, on every navigation, for a fact that does not change between them.
describe('two mounted headers', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    resetIdentity()
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    fetchMock.mockReset()
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => ({
        email: 'anna.ivanova@example.com',
        name: 'Анна Ковалёва',
        created_at: '2025-02-03T09:26:53Z',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
    resetIdentity()
  })

  it('issue exactly one GET /me between them', async () => {
    renderWithRouter(
      <>
        <ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />
        <ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="workspace" />
      </>,
    )

    // Both are waited for, so a second request had every chance to be issued and observed.
    await waitFor(() => {
      expect(screen.getByTestId('header-profile-button')).toHaveAttribute(
        'aria-label',
        'Меню профиля: Анна Ковалёва',
      )
      expect(screen.getByTestId('workspace-profile-button')).toHaveAttribute(
        'aria-label',
        'Меню профиля: Анна Ковалёва',
      )
    })

    expect(fetchMock.mock.calls.filter((call) => call[0] === '/api/v1/auth/me')).toHaveLength(1)
  })
})
