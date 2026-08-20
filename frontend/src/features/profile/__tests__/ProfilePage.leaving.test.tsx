import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { fetchAvatarBytes } from '../../../shared/identity/api/avatarApi'
import { stubObjectUrls } from './avatarTestSupport'

// Every way OFF this screen, and the one thing they share: an unsaved display name must not
// leave without the user saying so. The guard sits at the click seam because react-router
// navigation fires no `beforeunload` — a name typed and abandoned would vanish silently.

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})
vi.mock('../../../shared/identity/api/profileApi', () => ({
  fetchProfile: vi.fn(),
  saveProfileName: vi.fn(),
  NameRejectedError: class extends Error {},
}))
vi.mock('../../../shared/identity/api/avatarApi', () => ({
  fetchAvatarBytes: vi.fn(),
  uploadAvatar: vi.fn(),
  deleteAvatar: vi.fn(),
}))

const PROFILE = {
  email: 'anna.ivanova@example.com',
  name: null,
  createdAt: '2025-02-03T09:26:53Z',
  avatarUpdatedAt: null,
  hasPassword: true,
}

async function aReadyProfile() {
  renderWithRouter(<ProfilePage />)
  return screen.findByTestId('profile-to-projects')
}

describe('leaving the profile screen', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    vi.mocked(fetchAvatarBytes).mockResolvedValue(new Blob([new Uint8Array(8)]))
    vi.mocked(fetchProfile).mockResolvedValue(PROFILE)
  })

  it('goes to «Мои проекты» by its own route, not by browser history', async () => {
    // An explicit destination: this screen is reachable straight from a URL and from a fresh
    // tab, where `navigate(-1)` leaves the product entirely.
    const toProjects = await aReadyProfile()

    fireEvent.click(toProjects)

    expect(navigate).toHaveBeenCalledWith('/projects')
  })

  it('asks before leaving with an unsaved name, and stays when the answer is no', async () => {
    const toProjects = await aReadyProfile()
    fireEvent.change(await screen.findByTestId('profile-name-input'), {
      target: { value: 'Анна' },
    })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)

    fireEvent.click(toProjects)

    expect(confirm).toHaveBeenCalledWith('Имя не сохранено. Покинуть страницу профиля?')
    expect(navigate).not.toHaveBeenCalled()
    confirm.mockRestore()
  })

  it('leaves for the landing on «выйти», once the same guard allows it', async () => {
    // The account card's way out and the header menu's are the same handler: signing out is
    // leaving the screen, so it is guarded exactly like the projects link.
    await aReadyProfile()
    fireEvent.change(await screen.findByTestId('profile-name-input'), {
      target: { value: 'Анна' },
    })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const signOut = screen
      .getByTestId('profile-danger-zone')
      .querySelector('[data-testid="profile-logout-button"]') as HTMLElement

    fireEvent.click(signOut)
    expect(navigate).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    fireEvent.click(signOut)

    expect(navigate).toHaveBeenCalledWith('/')
    confirm.mockRestore()
  })

  it('offers browser history as the way back when the profile never loaded', async () => {
    // «Назад» rather than a projects link here: the failed screen has no identity, and the
    // history entry is the only destination that is certainly correct.
    vi.mocked(fetchProfile).mockRejectedValue(new Error('unavailable'))
    renderWithRouter(<ProfilePage />)

    fireEvent.click(await screen.findByText('Назад'))

    expect(navigate).toHaveBeenCalledWith(-1)
  })
})
