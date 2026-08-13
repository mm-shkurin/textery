import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { uploadAvatar } from '../../../shared/identity/api/avatarApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'

// Avatar scenario 4 — an SVG is refused by the CLIENT, before anything is sent.
//
// It is out of the `accept` attribute too, but `accept` is a hint: the file dialog may ignore it,
// and a drag or a scripted change never consults it at all. An SVG is a document that can carry
// script and this picture is rendered on every authenticated page, so the check is here rather
// than left to the server to decline after the bytes have already travelled.
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

const uploadAvatarMock = vi.mocked(uploadAvatar)

describe('picking an SVG', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    vi.mocked(fetchProfile).mockResolvedValue(profileWith({ avatarUpdatedAt: null }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('is refused inline and nothing is requested', async () => {
    renderWithRouter(<ProfilePage />)
    const input = await screen.findByTestId('avatar-file-input')

    const svg = new File(['<svg xmlns="http://www.w3.org/2000/svg"/>'], 'logo.svg', {
      type: 'image/svg+xml',
    })
    fireEvent.change(input, { target: { files: [svg] } })

    expect(await screen.findByTestId('avatar-rejection')).toHaveTextContent(
      'Подойдёт PNG, JPEG или WebP',
    )
    expect(uploadAvatarMock).not.toHaveBeenCalled()
    // Refused, not failed: nothing left the browser, so there is nothing to retry.
    expect(screen.queryByTestId('avatar-failed')).not.toBeInTheDocument()
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('АК')
  })
})
