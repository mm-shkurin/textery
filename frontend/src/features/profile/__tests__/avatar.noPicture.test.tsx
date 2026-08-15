import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { fetchAvatarBytes } from '../../../shared/identity/api/avatarApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'

// Avatar scenario 1 — no picture means NO REQUEST.
//
// `avatar_updated_at: null` is the whole answer: the bytes endpoint would 404, and asking anyway
// would put that 404 in the console of every page load of every account that never uploaded
// anything — which is most of them.
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

const fetchProfileMock = vi.mocked(fetchProfile)
const fetchAvatarBytesMock = vi.mocked(fetchAvatarBytes)

describe('an account with no avatar', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('shows initials and never asks for bytes', async () => {
    fetchProfileMock.mockResolvedValue(profileWith({ avatarUpdatedAt: null }))

    renderWithRouter(<ProfilePage />)

    expect(await screen.findByTestId('profile-identity-primary')).toHaveTextContent('Анна Ковалёва')
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('АК')
    expect(screen.queryByTestId('profile-avatar-picture')).not.toBeInTheDocument()
    expect(fetchAvatarBytesMock).not.toHaveBeenCalled()
  })
})
