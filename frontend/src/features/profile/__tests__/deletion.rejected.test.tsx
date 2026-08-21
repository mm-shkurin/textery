import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { requestAccountDeletion } from '../../../shared/identity/api/deleteAccountApi'
import { DeletionRejectedError } from '../../../shared/identity/api/profileErrors'
import { clearSession, getAccessToken, saveSession } from '../../../shared/session/authSession'
import { profileWith, stubObjectUrls } from './avatarTestSupport'
import { LANDING_MARKER, renderAtProfile } from './deletionTestSupport'

// Deletion scenario 4 — a refused confirmation is NOT a session ending.
//
// This is the one failure on this screen where treating a 400 as "you are signed out" would be
// actively wrong: the user typed the wrong password, nothing was deleted, and their session is
// exactly as valid as it was a second ago. Throwing them to the login screen would look like the
// deletion half-happened.
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

describe('a refused confirmation', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    vi.mocked(fetchProfile).mockResolvedValue(profileWith({ hasPassword: true }))
    vi.mocked(requestAccountDeletion).mockRejectedValue(
      new DeletionRejectedError('Подтверждение не принято. Проверьте введённое.'),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
    resetIdentity()
  })

  it('shows the message, keeps the session, and leaves the user on the screen', async () => {
    renderAtProfile(<ProfilePage />)

    fireEvent.click(await screen.findByTestId('account-delete-button'))
    fireEvent.change(screen.getByTestId('deletion-password-input'), {
      target: { value: 'wrong-password' },
    })
    fireEvent.click(screen.getByTestId('deletion-confirm-button'))

    expect(await screen.findByTestId('deletion-error')).toHaveTextContent(
      'Подтверждение не принято',
    )

    // The session is untouched — the account still exists and the user is still in it.
    await waitFor(() => expect(getAccessToken()).toBe('access-token'))
    expect(screen.getByTestId('profile-screen')).toBeInTheDocument()
    expect(screen.queryByTestId(LANDING_MARKER)).not.toBeInTheDocument()
    // The panel stays open with what was typed still in it: the fix is one character, not a
    // retype of the whole thing.
    expect(screen.getByTestId('deletion-password-input')).toHaveValue('wrong-password')
  })
})
