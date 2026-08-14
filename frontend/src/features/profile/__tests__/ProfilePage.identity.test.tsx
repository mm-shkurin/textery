import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfilePage } from '../components/ProfilePage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { fetchProfile } from '../../../shared/identity/api/profileApi'

// UI scenario 1 — the screen renders the account `GET /me` describes, in both of its shapes.
vi.mock('../../../shared/identity/api/profileApi', () => ({
  fetchProfile: vi.fn(),
  saveProfileName: vi.fn(),
  NameRejectedError: class extends Error {},
}))

const fetchProfileMock = vi.mocked(fetchProfile)

describe('ProfilePage identity', () => {
  beforeEach(() => {
    resetIdentity()
    fetchProfileMock.mockReset()
  })

  it('shows the name, the address and the registration date', async () => {
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: 'Анна Ковалёва',
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: null,
    })

    renderWithRouter(<ProfilePage />)

    expect(await screen.findByTestId('profile-identity-primary')).toHaveTextContent('Анна Ковалёва')
    expect(screen.getByTestId('profile-identity-secondary')).toHaveTextContent(
      'anna.ivanova@example.com',
    )
    // The YEAR is the assertion, not decoration: `formatCardDate` hides it whenever it matches the
    // current year, which would render an account opened this year as «На Textery с 3 февраля».
    expect(screen.getByTestId('profile-since')).toHaveTextContent('На Textery с 3 февраля 2025')
    // Initials from the NAME, and only because there is one.
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('АК')
  })

  // `name: null` is the one stored representation of "no name" — an account that never had one and
  // an account that cleared one are the same screen.
  it('falls back to the address as the identity when no name is set', async () => {
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: null,
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: null,
    })

    renderWithRouter(<ProfilePage />)

    expect(await screen.findByTestId('profile-identity-primary')).toHaveTextContent(
      'anna.ivanova@example.com',
    )
    expect(screen.getByTestId('profile-identity-secondary')).toHaveTextContent('Имя не задано')
    // «AI» — from `anna.ivanova`, the address's two words. The avatar must not go blank just
    // because the name did.
    expect(screen.getAllByTestId('profile-avatar-ready')[0]).toHaveTextContent('AI')
  })
})
