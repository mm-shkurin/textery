import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile, saveProfileName } from '../../../shared/identity/api/profileApi'

// UI scenario 2 — saving a name sends exactly ONE PATCH and updates the header from its response.
vi.mock('../../../shared/identity/api/profileApi', () => ({
  fetchProfile: vi.fn(),
  saveProfileName: vi.fn(),
  NameRejectedError: class extends Error {},
}))

const fetchProfileMock = vi.mocked(fetchProfile)
const saveProfileNameMock = vi.mocked(saveProfileName)

describe('ProfilePage saving a name', () => {
  beforeEach(() => {
    resetIdentity()
    fetchProfileMock.mockReset()
    saveProfileNameMock.mockReset()
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: null,
      createdAt: '2025-02-03T09:26:53Z',
    })
  })

  it('sends one PATCH for a double click and updates the header without a reload', async () => {
    // The response carries the NORMALIZED value — a trailing space comes back trimmed. Everything
    // downstream (the header, the dirty flag) has to be recomputed against THIS, not against what
    // was typed, or the name stays "unsaved" forever after a successful save.
    saveProfileNameMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: 'Анна Ковалёва',
      createdAt: '2025-02-03T09:26:53Z',
    })

    renderWithRouter(<ProfilePage />)

    const input = await screen.findByTestId('profile-name-input')
    fireEvent.change(input, { target: { value: 'Анна Ковалёва ' } })

    const save = screen.getByTestId('profile-name-save')
    fireEvent.click(save)
    fireEvent.click(save)

    await waitFor(() => expect(saveProfileNameMock).toHaveBeenCalledTimes(1))
    // Trimmed and NFC-normalized before it leaves — the same value the counter measured.
    expect(saveProfileNameMock).toHaveBeenCalledWith('Анна Ковалёва')

    // The header reads the same identity snapshot the PATCH response replaced. No second GET, no
    // reload: the menu's accessible name carries the new identity.
    await waitFor(() =>
      expect(screen.getByTestId('profile-profile-button')).toHaveAttribute(
        'aria-label',
        'Меню профиля: Анна Ковалёва',
      ),
    )
    expect(fetchProfileMock).toHaveBeenCalledTimes(1)

    // Dirty flag recomputed against the RESPONSE: the field holds «Анна Ковалёва», the server
    // stored «Анна Ковалёва», so there is nothing left to save.
    expect(screen.getByTestId('profile-name-save')).toBeDisabled()
  })

  // Clearing is first-class: an empty field plus save means "remove my name", and the account
  // falls back to its address everywhere — screen and header alike.
  it('clears the name and falls back to the address', async () => {
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: 'Анна Ковалёва',
      createdAt: '2025-02-03T09:26:53Z',
    })
    saveProfileNameMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: null,
      createdAt: '2025-02-03T09:26:53Z',
    })

    renderWithRouter(<ProfilePage />)

    fireEvent.change(await screen.findByTestId('profile-name-input'), { target: { value: '' } })
    fireEvent.click(screen.getByTestId('profile-name-save'))

    await waitFor(() => expect(saveProfileNameMock).toHaveBeenCalledWith(''))
    expect(await screen.findByTestId('profile-identity-primary')).toHaveTextContent(
      'anna.ivanova@example.com',
    )
    // Initials fall back to the address with the name — «AI», not a blank disc.
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('AI')
  })
})
