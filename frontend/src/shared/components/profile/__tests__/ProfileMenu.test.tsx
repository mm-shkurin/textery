import { describe, expect, it, vi, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProfileMenu } from '../ProfileMenu'
import { clearSession, saveSession } from '../../../../features/auth/utils/authSession'

function signIn(email: string): void {
  const encode = (value: object) =>
    btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(value))))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')
  const token = `${encode({ alg: 'HS256' })}.${encode({ email, type: 'access' })}.sig`
  saveSession({ accessToken: token, refreshToken: token })
}

describe('ProfileMenu', () => {
  afterEach(() => {
    clearSession()
  })

  it('keeps the menu closed until the avatar is clicked', () => {
    signIn('emailname@gmail.com')
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
    expect(screen.getByTestId('header-profile-button')).toHaveAttribute('aria-expanded', 'false')
  })

  // The address is the whole reason the menu has a header row: it is how a user with two accounts
  // knows which one this tab is in.
  it('shows the signed-in address from the access token', () => {
    signIn('emailname@gmail.com')
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    fireEvent.click(screen.getByTestId('header-profile-button'))

    expect(screen.getByTestId('header-profile-email')).toHaveTextContent('emailname@gmail.com')
    expect(screen.getByTestId('header-profile-button')).toHaveAttribute('aria-expanded', 'true')
  })

  // A session whose token carries no readable address is still a session: the menu must open and
  // must still offer the way out. What it must NOT do is print a stand-in address.
  it('still opens, without an address row, when the token carries no email claim', () => {
    saveSession({ accessToken: 'opaque-token', refreshToken: 'opaque-token' })
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    fireEvent.click(screen.getByTestId('header-profile-button'))

    expect(screen.queryByTestId('header-profile-email')).not.toBeInTheDocument()
    expect(screen.getByTestId('header-logout-button')).toBeInTheDocument()
  })

  it('signs out from the menu item and closes the menu', () => {
    signIn('emailname@gmail.com')
    const onLogoutClick = vi.fn()
    render(<ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="header" />)

    fireEvent.click(screen.getByTestId('header-profile-button'))
    fireEvent.click(screen.getByTestId('header-logout-button'))

    expect(onLogoutClick).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
  })

  // An overlay that only closes by re-clicking its own trigger is a trap: it covers the page and
  // the obvious gesture — click somewhere else — does nothing.
  it('closes when the user presses somewhere else on the page', () => {
    signIn('emailname@gmail.com')
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    fireEvent.click(screen.getByTestId('header-profile-button'))
    fireEvent.mouseDown(document.body)

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
  })

  // Escape must also put focus back on the trigger — a keyboard user who closes the menu and is
  // dropped on <body> has to tab the whole document to get back to where they were.
  it('closes on Escape and returns focus to the avatar', () => {
    signIn('emailname@gmail.com')
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)

    fireEvent.click(screen.getByTestId('header-profile-button'))
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByTestId('header-profile-menu')).not.toBeInTheDocument()
    expect(document.activeElement).toBe(screen.getByTestId('header-profile-button'))
  })

  // Two menus are on screen across the app; a shared id would make "click sign-out" ambiguous.
  it('scopes its test ids to the header it belongs to', () => {
    signIn('emailname@gmail.com')
    render(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="workspace" />)

    fireEvent.click(screen.getByTestId('workspace-profile-button'))

    expect(screen.getByTestId('workspace-logout-button')).toBeInTheDocument()
    expect(screen.queryByTestId('header-logout-button')).not.toBeInTheDocument()
  })
})
