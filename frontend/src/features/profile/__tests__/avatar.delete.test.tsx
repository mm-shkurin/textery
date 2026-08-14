import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { deleteAvatar, fetchAvatarBytes } from '../../../shared/identity/api/avatarApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'

// Avatar scenario 5 — deleting the picture falls back to initials everywhere, from the DELETE
// response alone. No reload, no second `GET /me`: the response is the full profile, and its
// `avatar_updated_at: null` is what tells every mounted avatar to drop the picture.
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

const deleteAvatarMock = vi.mocked(deleteAvatar)

describe('deleting the avatar', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('puts initials back in the header', async () => {
    vi.mocked(fetchProfile).mockResolvedValue(
      profileWith({ avatarUpdatedAt: '2026-08-13T10:00:00Z' }),
    )
    vi.mocked(fetchAvatarBytes).mockResolvedValue(new Blob([new Uint8Array(1024)]))
    deleteAvatarMock.mockResolvedValue(profileWith({ avatarUpdatedAt: null }))

    renderWithRouter(<ProfilePage />)
    // The picture is on screen first, so what follows is a change rather than an initial render.
    await screen.findAllByTestId('profile-avatar-picture')

    fireEvent.click(screen.getByTestId('avatar-delete-button'))

    await waitFor(() => expect(deleteAvatarMock).toHaveBeenCalledTimes(1))
    await waitFor(() =>
      expect(screen.queryByTestId('profile-avatar-picture')).not.toBeInTheDocument(),
    )
    // The header's own avatar — the one on every page — is back to initials, not blank.
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('АК')
    // And the «Удалить» button is gone with the picture it removed.
    expect(screen.queryByTestId('avatar-delete-button')).not.toBeInTheDocument()
  })
})
