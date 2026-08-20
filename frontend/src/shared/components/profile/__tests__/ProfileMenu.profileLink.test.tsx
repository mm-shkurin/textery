import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProfileMenu } from '../ProfileMenu'
import { clearSession, saveSession } from '../../../session/authSession'
import { resetIdentity } from '../../../identity/identityStore'
import { fetchProfile } from '../../../identity/api/profileApi'

vi.mock('../../../identity/api/profileApi', () => ({ fetchProfile: vi.fn() }))

const fetchProfileMock = vi.mocked(fetchProfile)

// A real route at /profile so the assertion is "the user ARRIVED there", not "a navigate spy was
// called with a string" — the latter passes just as happily against a path that routes nowhere.
function renderMenu() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />} />
        <Route path="/profile" element={<p data-testid="profile-screen">Профиль</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProfileMenu «Мой профиль»', () => {
  beforeEach(() => {
    resetIdentity()
    fetchProfileMock.mockReset()
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: 'Анна Ковалёва',
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: null,
    })
  })

  afterEach(() => {
    clearSession()
    resetIdentity()
  })

  it('navigates to the profile screen and leaves no menu behind', async () => {
    renderMenu()
    await waitFor(() => expect(fetchProfileMock).toHaveBeenCalled())
    fireEvent.click(await screen.findByTestId('header-profile-button'))

    fireEvent.click(screen.getByTestId('header-profile-link'))

    expect(await screen.findByTestId('profile-screen')).toBeInTheDocument()
    // The panel is closed by the click itself, not merely unmounted with the route: a menu left
    // open would be the last frame the user sees over the screen they just left.
    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
  })
})
