import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { fetchAvatarBytes, uploadAvatar } from '../../../shared/identity/api/avatarApi'
import { AVATAR_EDGE_PX } from '../utils/avatarImage'
import { profileWith, stubCanvasPipeline, stubObjectUrls } from './avatarTestSupport'

// Avatar scenario 3 — what leaves the browser is the RESIZED image, not the file that was picked.
//
// Without this the feature does not work at all: a photograph off a phone is several megabytes and
// the server's bound is a fraction of that, so every real upload would be refused. jsdom has no
// encoder, so the encoder is stubbed and what is asserted is the plumbing around it — that the
// canvas was 256×256 and that the bytes sent are its output rather than the File.
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
const uploadAvatarMock = vi.mocked(uploadAvatar)

const FOUR_MEGABYTES = 4 * 1024 * 1024

describe('uploading a photograph', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    vi.restoreAllMocks()
    stubObjectUrls()
    fetchProfileMock.mockResolvedValue(profileWith({ avatarUpdatedAt: null }))
    vi.mocked(fetchAvatarBytes).mockResolvedValue(new Blob([new Uint8Array(8)]))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    resetIdentity()
  })

  it('downscales a 4 MB picture before sending it', async () => {
    const encoded = stubCanvasPipeline({ width: 3024, height: 4032 })
    uploadAvatarMock.mockResolvedValue(profileWith({ avatarUpdatedAt: '2026-08-13T10:00:00Z' }))

    renderWithRouter(<ProfilePage />)
    const input = await screen.findByTestId('avatar-file-input')

    const source = new File([new Uint8Array(FOUR_MEGABYTES)], 'photo.jpg', { type: 'image/jpeg' })
    fireEvent.change(input, { target: { files: [source] } })

    await waitFor(() => expect(uploadAvatarMock).toHaveBeenCalledTimes(1))

    const sent = uploadAvatarMock.mock.calls[0][0]
    expect(sent.size).toBeLessThan(source.size)
    // The canvas is square at the target edge, so a 3:4 portrait is centre-cropped rather than
    // squashed — a full-frame draw into a square canvas would deform the face.
    expect(encoded).toEqual([
      { width: AVATAR_EDGE_PX, height: AVATAR_EDGE_PX, type: 'image/webp', quality: 0.85 },
    ])
  })
})
