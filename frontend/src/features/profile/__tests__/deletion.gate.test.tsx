import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { requestAccountDeletion } from '../../../shared/identity/api/deleteAccountApi'
import { profileWith, stubObjectUrls } from './avatarTestSupport'
import { renderAtProfile } from './deletionTestSupport'

// Deletion scenarios 1 and 5 — the button does not delete, and cancelling sends nothing.
//
// This is the one irreversible operation in the product: there is no undo and no bin. A single
// button that deleted on click would be one mis-click away from destroying everything a user has
// written, so the button's ONLY job is to ask.
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

describe('the delete button', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    vi.mocked(fetchProfile).mockResolvedValue(profileWith({ hasPassword: true }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('opens a confirmation instead of deleting', async () => {
    renderAtProfile(<ProfilePage />)

    fireEvent.click(await screen.findByTestId('account-delete-button'))

    expect(screen.getByTestId('account-delete-confirm')).toBeInTheDocument()
    expect(screen.getByTestId('deletion-password-input')).toBeInTheDocument()
    // Nothing has been asked of the backend. The account is untouched.
    expect(requestDeletionMock).not.toHaveBeenCalled()
    // And the confirmation cannot be submitted while the field is empty.
    expect(screen.getByTestId('deletion-confirm-button')).toBeDisabled()
  })

  it('sends nothing when the confirmation is cancelled', async () => {
    renderAtProfile(<ProfilePage />)

    fireEvent.click(await screen.findByTestId('account-delete-button'))
    fireEvent.change(screen.getByTestId('deletion-password-input'), {
      target: { value: 'Str0ng!Pass' },
    })
    fireEvent.click(screen.getByTestId('deletion-cancel-button'))

    expect(screen.queryByTestId('account-delete-confirm')).not.toBeInTheDocument()
    expect(requestDeletionMock).not.toHaveBeenCalled()
    // Backing out is free, and reopening starts from an empty field rather than from the password
    // the user just decided not to use.
    fireEvent.click(screen.getByTestId('account-delete-button'))
    expect(screen.getByTestId('deletion-password-input')).toHaveValue('')
  })
})
