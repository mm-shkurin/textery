import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { ProfileMenu } from '../ProfileMenu'
import { clearSession, saveSession } from '../../../../features/auth/utils/authSession'
import { resetIdentity } from '../../../identity/identityStore'
import { fetchProfile } from '../../../identity/api/profileApi'

// The identity is stubbed at the API CLIENT, not by planting a token in sessionStorage. It used to
// be the latter, back when the address was decoded out of the access token — and that is exactly
// the regression story 13 had to avoid: those tests kept passing while covering nothing, because
// the string they stored is not a JWT and the path they meant to exercise had moved to `GET /me`.
vi.mock('../../../identity/api/profileApi', () => ({ fetchProfile: vi.fn() }))

const fetchProfileMock = vi.mocked(fetchProfile)

function signedInAs(name: string | null, email: string): void {
  saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
  fetchProfileMock.mockResolvedValue({
    email,
    name,
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: null,
  })
}

async function openMenu(prefix: string): Promise<void> {
  // Awaited: the identity arrives from a promise, and clicking before it lands would assert
  // against the loading state rather than the one under test.
  await waitFor(() => expect(fetchProfileMock).toHaveBeenCalled())
  fireEvent.click(await screen.findByTestId(`${prefix}-profile-button`))
}

describe('ProfileMenu', () => {
  beforeEach(() => {
    resetIdentity()
    fetchProfileMock.mockReset()
  })

  afterEach(() => {
    clearSession()
    resetIdentity()
  })

  it('keeps the menu closed until the avatar is clicked', () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
    expect(screen.getByTestId('header-profile-button')).toHaveAttribute('aria-expanded', 'false')
  })

  // The identity row is the whole reason the panel has a header: it is how a user with two
  // accounts knows which one this tab is in. With a name set, the name is what it says.
  it('shows the signed-in identity from /me', async () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    await openMenu('header')

    expect(screen.getByTestId('header-profile-email')).toHaveTextContent('Анна Ковалёва')
    expect(screen.getByTestId('header-profile-button')).toHaveAttribute('aria-expanded', 'true')
  })

  it('falls back to the address when no name is set', async () => {
    signedInAs(null, 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    await openMenu('header')

    expect(screen.getByTestId('header-profile-email')).toHaveTextContent('anna.ivanova@example.com')
  })

  it('signs out from the menu item and closes the menu', async () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    const onLogoutClick = vi.fn()
    renderWithRouter(<ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="header" />)

    await openMenu('header')
    fireEvent.click(screen.getByTestId('header-logout-button'))

    expect(onLogoutClick).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
  })

  // An overlay that only closes by re-clicking its own trigger is a trap: it covers the page and
  // the obvious gesture — click somewhere else — does nothing.
  it('closes when the user presses somewhere else on the page', async () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    await openMenu('header')
    fireEvent.mouseDown(document.body)

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
  })

  // Escape must also put focus back on the trigger — a keyboard user who closes the menu and is
  // dropped on <body> has to tab the whole document to get back to where they were.
  it('closes on Escape and returns focus to the avatar', async () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    await openMenu('header')
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
    expect(document.activeElement).toBe(screen.getByTestId('header-profile-button'))
  })

  // Several menus are on screen across the app; a shared id would make "click sign-out"
  // ambiguous.
  it('scopes its test ids to the header it belongs to', async () => {
    signedInAs('Анна Ковалёва', 'anna.ivanova@example.com')
    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="workspace" />)

    await openMenu('workspace')

    expect(screen.getByTestId('workspace-logout-button')).toBeInTheDocument()
    expect(screen.queryByTestId('header-logout-button')).not.toBeInTheDocument()
  })
})
