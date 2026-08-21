import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile, saveProfileName } from '../../../shared/identity/api/profileApi'
import {
  deleteAvatar,
  fetchAvatarBytes,
  uploadAvatar,
} from '../../../shared/identity/api/avatarApi'
import { stubCanvasPipeline, stubObjectUrls } from './avatarTestSupport'

// Every way out of a failure this screen offers. All three are «Повторить» buttons, and each is
// the only thing standing between the user and a dead end: a request that never answered leaves
// nothing else on screen to act on, and a spinner with no bound is indistinguishable from a hung
// tab. The load failure additionally has to leave the SESSION alone — an unprompted `GET /me`
// must never sign anybody out.

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

function aPicture(): File {
  return new File([new Uint8Array(1024)], 'photo.png', { type: 'image/png' })
}

describe('recovering from a failure', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    vi.restoreAllMocks()
    stubObjectUrls()
    vi.mocked(fetchAvatarBytes).mockResolvedValue(new Blob([new Uint8Array(8)]))
    vi.mocked(fetchProfile).mockResolvedValue(PROFILE)
  })

  it('offers a retry when the profile could not be loaded, and loads it on the second try', async () => {
    // The failure did not end the session, so this screen must be usable rather than replaced by
    // a login redirect.
    vi.mocked(fetchProfile).mockRejectedValueOnce(new Error('unavailable'))

    renderWithRouter(<ProfilePage />)
    const retry = await screen.findByTestId('profile-load-retry')

    fireEvent.click(retry)

    // The value, not the mere presence: a retry that re-rendered the card from a failed read
    // would satisfy `toBeTruthy` with an empty field.
    expect(await screen.findByTestId('profile-name-input')).toHaveValue('')
    expect(screen.getByText(PROFILE.email)).toBeInTheDocument()
    expect(screen.queryByTestId('profile-load-failed')).toBeNull()
  })

  it('keeps the typed name and retries the save that never reached the server', async () => {
    // A banner above the filled-in card, not an inline field error: the field is not what is
    // wrong, and the value the user typed is still theirs.
    vi.mocked(saveProfileName)
      .mockRejectedValueOnce(new Error('no answer'))
      .mockResolvedValueOnce({ ...PROFILE, name: 'Анна Ковалёва' })

    renderWithRouter(<ProfilePage />)
    const input = await screen.findByTestId('profile-name-input')
    fireEvent.change(input, { target: { value: 'Анна Ковалёва' } })
    fireEvent.click(screen.getByTestId('profile-name-save'))

    const banner = await screen.findByTestId('profile-save-failed')
    expect((input as HTMLInputElement).value).toBe('Анна Ковалёва')

    fireEvent.click(banner.querySelector('button') as HTMLButtonElement)

    await waitFor(() => expect(saveProfileName).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByTestId('profile-save-failed')).toBeNull())
  })

  it('retries an upload without asking for the file again', async () => {
    // The expensive half — decode and re-encode — is already done, and the file input has been
    // reset by then, so a retry that needed the File would have nothing to work with.
    stubCanvasPipeline({ width: 900, height: 600 })
    vi.mocked(uploadAvatar)
      .mockRejectedValueOnce(new Error('no answer'))
      .mockResolvedValueOnce({ ...PROFILE, avatarUpdatedAt: '2026-08-14T12:00:00Z' })

    renderWithRouter(<ProfilePage />)
    const input = await screen.findByTestId('avatar-file-input')
    fireEvent.change(input, { target: { files: [aPicture()] } })

    const banner = await screen.findByTestId('avatar-failed')
    fireEvent.click(banner.querySelector('button') as HTMLButtonElement)

    await waitFor(() => expect(uploadAvatar).toHaveBeenCalledTimes(2))
    expect(vi.mocked(uploadAvatar).mock.calls[1][0]).toBe(vi.mocked(uploadAvatar).mock.calls[0][0])
  })

  it('opens the file dialog through the visible button, never the bare input', async () => {
    // A file input cannot be styled and reads as a form nobody designed, so the button is the
    // only visible control and its whole job is to forward the click.
    renderWithRouter(<ProfilePage />)
    const input = (await screen.findByTestId('avatar-file-input')) as HTMLInputElement
    const opened = vi.spyOn(input, 'click')

    fireEvent.click(screen.getByTestId('avatar-upload-button'))

    expect(opened).toHaveBeenCalledTimes(1)
  })

  it('clears the input so re-picking the same file is still a change event', async () => {
    // Picking the SAME file twice fires no `change` at all otherwise, and a user who fixed
    // nothing and re-picked would think the app had frozen.
    stubCanvasPipeline({ width: 900, height: 600 })
    vi.mocked(uploadAvatar).mockResolvedValue({
      ...PROFILE,
      avatarUpdatedAt: '2026-08-14T12:00:00Z',
    })

    renderWithRouter(<ProfilePage />)
    const input = (await screen.findByTestId('avatar-file-input')) as HTMLInputElement
    fireEvent.change(input, { target: { files: [aPicture()] } })

    await waitFor(() => expect(uploadAvatar).toHaveBeenCalledTimes(1))
    expect(input.value).toBe('')
  })

  it('removes a stored picture through the delete button', async () => {
    vi.mocked(fetchProfile).mockResolvedValue({
      ...PROFILE,
      avatarUpdatedAt: '2026-08-14T12:00:00Z',
    })
    vi.mocked(deleteAvatar).mockResolvedValue(PROFILE)

    renderWithRouter(<ProfilePage />)
    fireEvent.click(await screen.findByTestId('avatar-delete-button'))

    await waitFor(() => expect(deleteAvatar).toHaveBeenCalledTimes(1))
  })
})
