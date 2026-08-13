import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'

// UI scenario 3 — the counter counts what the SERVER counts.
//
// The emoji is the whole point: U+1F642 is one code point and TWO UTF-16 units, so a counter
// written with `.length` reads 120 for a name the domain measures as 60 and refuses to save a
// value the backend answers 200 to. The disagreement is invisible on ASCII and total on emoji.
vi.mock('../../../shared/identity/api/profileApi', () => ({
  fetchProfile: vi.fn(),
  saveProfileName: vi.fn(),
  NameRejectedError: class extends Error {},
}))

const fetchProfileMock = vi.mocked(fetchProfile)
const EMOJI = '🙂'

describe('ProfilePage name counter', () => {
  beforeEach(() => {
    resetIdentity()
    fetchProfileMock.mockReset()
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: null,
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: null,
    })
  })

  it('reads 60 emoji as 60 and leaves the save available', async () => {
    renderWithRouter(<ProfilePage />)

    const input = await screen.findByTestId('profile-name-input')
    fireEvent.change(input, { target: { value: EMOJI.repeat(60) } })

    expect(screen.getByTestId('profile-name-counter')).toHaveTextContent('60 / 60')
    expect(screen.getByTestId('profile-name-save')).toBeEnabled()
    expect(screen.queryByTestId('profile-name-error')).not.toBeInTheDocument()
  })

  it('marks 61 as over the limit and refuses to send it', async () => {
    renderWithRouter(<ProfilePage />)

    const input = await screen.findByTestId('profile-name-input')
    fireEvent.change(input, { target: { value: EMOJI.repeat(61) } })

    expect(screen.getByTestId('profile-name-counter')).toHaveTextContent('61 / 60')
    expect(screen.getByTestId('profile-name-save')).toBeDisabled()
    // The count is in the sentence: «слишком длинное» leaves the user to work out by how much.
    expect(screen.getByTestId('profile-name-error')).toHaveTextContent(
      'Имя длиннее 60 символов — сейчас 61.',
    )
    // The typed value STAYS — the user shortens what they wrote rather than typing it again.
    expect(input).toHaveValue(EMOJI.repeat(61))
  })
})
