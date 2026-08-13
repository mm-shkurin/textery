import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { requestAccountDeletion } from '../../../shared/identity/api/deleteAccountApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'
import { renderAtProfile } from './deletionTestSupport'

// Deletion scenario 2 — an account with no password confirms by typing its own address, and only
// an exact match unlocks the button.
//
// An OAuth-only account has no password to type. Asking for one would be a door with no key: the
// user could not leave the product by any route the product offers.
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
vi.mock('../../../shared/identity/api/deleteAccountApi', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  requestAccountDeletion: vi.fn(),
}))

const requestDeletionMock = vi.mocked(requestAccountDeletion)
const EMAIL = 'anna.ivanova@example.com'

describe('an account with no password', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    vi.mocked(fetchProfile).mockResolvedValue(profileWith({ email: EMAIL, hasPassword: false }))
    requestDeletionMock.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('unlocks only on an exact address, and sends the address form', async () => {
    renderAtProfile(<ProfilePage />)

    fireEvent.click(await screen.findByTestId('account-delete-button'))
    // No password field anywhere on the screen — this account has none.
    expect(screen.queryByTestId('deletion-password-input')).not.toBeInTheDocument()

    const input = screen.getByTestId('deletion-email-input')
    // A near miss is a miss: same domain, different local part.
    fireEvent.change(input, { target: { value: 'anna.ivanoya@example.com' } })
    expect(screen.getByTestId('deletion-confirm-button')).toBeDisabled()

    // Case matters too — the gesture is proving you know which account this is.
    fireEvent.change(input, { target: { value: EMAIL.toUpperCase() } })
    expect(screen.getByTestId('deletion-confirm-button')).toBeDisabled()

    fireEvent.click(screen.getByTestId('deletion-confirm-button'))
    expect(requestDeletionMock).not.toHaveBeenCalled()

    fireEvent.change(input, { target: { value: EMAIL } })
    expect(screen.getByTestId('deletion-confirm-button')).toBeEnabled()
    fireEvent.click(screen.getByTestId('deletion-confirm-button'))

    // The `confirm_email` shape, not the password one — which shape is sent is the ACCOUNT's
    // decision, carried by `has_password`, never the client's preference.
    await waitFor(() =>
      expect(requestDeletionMock).toHaveBeenCalledWith({ kind: 'email', email: EMAIL }),
    )
    expect(requestDeletionMock).toHaveBeenCalledTimes(1)
  })
})
