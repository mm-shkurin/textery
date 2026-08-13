import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfileMenu } from '../../../shared/components/profile/ProfileMenu'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { fetchAvatarBytes } from '../../../shared/identity/api/avatarApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'

// Avatar scenario 2 — the picture is downloaded ONCE per page, however many avatars are mounted.
//
// This is also the scenario that pins the reason the feature is built this way at all: the <img>
// cannot point at the endpoint, because the browser would send that request with no
// `Authorization` header and get a 401. The bytes come through the app, with the token, and every
// mounted avatar shares the one object URL made from them.
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

describe('two mounted avatars with a picture', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('fetch the bytes exactly once and both show the picture', async () => {
    fetchProfileMock.mockResolvedValue(profileWith({ avatarUpdatedAt: '2026-08-13T10:00:00Z' }))
    fetchAvatarBytesMock.mockResolvedValue(new Blob([new Uint8Array(1024)], { type: 'image/webp' }))

    renderWithRouter(
      <>
        <ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />
        <ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="workspace" />
      </>,
    )

    const pictures = await screen.findAllByTestId('profile-avatar-picture')
    expect(pictures).toHaveLength(2)
    // One object URL, shared. Two would mean two downloads and two things to revoke, one of which
    // nothing is holding a reference to.
    expect(pictures[0]).toHaveAttribute('src', 'blob:avatar-1')
    expect(pictures[1]).toHaveAttribute('src', 'blob:avatar-1')

    // Waited past the point a second request could have been issued and observed.
    await waitFor(() => expect(fetchAvatarBytesMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByText('АК')).not.toBeInTheDocument()
  })
})
