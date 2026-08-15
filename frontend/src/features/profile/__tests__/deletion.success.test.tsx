import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'
import { requestAccountDeletion } from '../../../shared/identity/api/deleteAccountApi'
import { clearSession, getAccessToken, saveSession } from '../../../features/auth/utils/authSession'
import { profileWith, stubObjectUrls } from './avatarTestSupport'
import { LANDING_MARKER, renderAtProfile } from './deletionTestSupport'

// Deletion scenario 3 — the exit.
//
// The 204 does not invalidate the access token: these are stateless JWTs, so the one in this tab
// stays valid-looking for up to fifteen more minutes while the backend answers 401 to it, because
// the account behind it is gone. Leave the session in place, or leave a `/me` in flight, and the
// last thing the user sees on their way out of the product is «Сессия истекла» — an error report
// for an operation that succeeded exactly as they asked.
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

describe('a confirmed deletion', () => {
  beforeEach(() => {
    resetIdentity()
    vi.clearAllMocks()
    stubObjectUrls()
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    vi.mocked(fetchProfile).mockResolvedValue(profileWith({ hasPassword: true }))
    vi.mocked(requestAccountDeletion).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
    resetIdentity()
  })

  it('clears the session and lands on the landing page, with no expired-session screen', async () => {
    renderAtProfile(<ProfilePage />)

    fireEvent.click(await screen.findByTestId('account-delete-button'))
    fireEvent.change(screen.getByTestId('deletion-password-input'), {
      target: { value: 'Str0ng!Pass' },
    })
    fireEvent.click(screen.getByTestId('deletion-confirm-button'))

    await waitFor(() => expect(screen.getByTestId(LANDING_MARKER)).toBeInTheDocument())

    // The tokens are gone, so nothing in this tab can start another authenticated request.
    expect(getAccessToken()).toBeNull()
    // The profile screen is not merely hidden behind the landing — it is unmounted, so no header
    // is left rendering the deleted account's identity.
    expect(screen.queryByTestId('profile-screen')).not.toBeInTheDocument()
    expect(screen.queryByTestId('profile-danger-zone')).not.toBeInTheDocument()
    // And the way out did not end in an error about the session the user just ended.
    expect(screen.queryByText(/Сессия истекла/)).not.toBeInTheDocument()
  })
})
