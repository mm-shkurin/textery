import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../test/renderWithRouter'
import { ProfileMenu } from '../../components/profile/ProfileMenu'
import { clearSession, saveSession } from '../../../features/auth/utils/authSession'
import { resetIdentity } from '../../identity/identityStore'
import { fetchProfile } from '../../identity/api/profileApi'
import { initTheme, resetTheme, setTheme, subscribeTheme, themeSnapshot } from '../themeStore'
import { THEME_ATTRIBUTE, THEME_STORAGE_KEY } from '../theme'
import { runThemeBootScript } from './bootScript'

vi.mock('../../identity/api/profileApi', () => ({ fetchProfile: vi.fn() }))
const fetchProfileMock = vi.mocked(fetchProfile)

// `null` means the platform has no `matchMedia` at all, which is jsdom's real state and also that
// of a few embedded webviews. It is a distinct case from "matchMedia says light": the first one
// throws if the production code forgets to guard the call.
function systemPrefers(mode: 'dark' | 'light' | null): void {
  if (mode === null) {
    Reflect.deleteProperty(window, 'matchMedia')
    return
  }
  window.matchMedia = ((query: string) => ({
    matches: mode === 'dark' && query === '(prefers-color-scheme: dark)',
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as typeof window.matchMedia
}

// What a page load does: nothing is on <html> yet, and the boot script decides.
function loadPage(): string | null {
  document.documentElement.removeAttribute(THEME_ATTRIBUTE)
  runThemeBootScript()
  return document.documentElement.getAttribute(THEME_ATTRIBUTE)
}

describe('theme selection', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
    systemPrefers(null)
    resetIdentity()
    fetchProfileMock.mockReset()
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
    clearSession()
    resetIdentity()
  })

  // 1. Nothing stored, nothing preferred.
  it('defaults to light with no stored choice and no system preference', () => {
    expect(loadPage()).toBe('light')

    // The other shape of "no preference": matchMedia exists and answers no.
    systemPrefers('light')
    expect(loadPage()).toBe('light')
  })

  // 3. The OS decides when the user has not.
  it('follows a dark system preference when nothing is stored', () => {
    systemPrefers('dark')

    expect(loadPage()).toBe('dark')
    // And it is NOT written back: recording a system-derived value as a choice would freeze the
    // page at today's OS setting and stop it following the next change.
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull()
  })

  // 4. An explicit choice outranks the OS, in both directions.
  it('lets a stored choice override the system preference', () => {
    systemPrefers('dark')
    localStorage.setItem(THEME_STORAGE_KEY, 'light')
    expect(loadPage()).toBe('light')

    systemPrefers('light')
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    expect(loadPage()).toBe('dark')
  })

  // 2. The switch itself, end to end: menu click -> attribute -> storage -> next page load.
  it('switches from the profile menu and survives a reload', async () => {
    saveSession({ accessToken: 'access-token', refreshToken: 'refresh-token' })
    fetchProfileMock.mockResolvedValue({
      email: 'anna.ivanova@example.com',
      name: 'Анна Ковалёва',
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: null,
    })
    expect(loadPage()).toBe('light')
    resetTheme()

    renderWithRouter(<ProfileMenu onLogoutClick={vi.fn()} testIdPrefix="header" />)
    await waitFor(() => expect(fetchProfileMock).toHaveBeenCalled())
    fireEvent.click(await screen.findByTestId('header-profile-button'))

    const toggle = screen.getByTestId('header-theme-toggle')
    expect(toggle).toHaveTextContent('Тема: светлая')
    expect(toggle).toHaveAttribute('aria-checked', 'false')

    fireEvent.click(toggle)

    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, 'dark')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    // The panel stays open and the row re-labels itself, so the user can switch back without
    // reopening the menu.
    expect(screen.getByTestId('header-theme-toggle')).toHaveTextContent('Тема: тёмная')
    expect(screen.getByTestId('header-theme-toggle')).toHaveAttribute('aria-checked', 'true')

    // The reload. Nothing on <html>, boot script runs again, and the stored choice is what it
    // finds — including against an OS that says the opposite.
    systemPrefers('light')
    expect(loadPage()).toBe('dark')
  })

  // Safari in private mode does not return null from `localStorage` — it THROWS. An unguarded read
  // would take the exception out of the boot script, leaving <html> with no attribute at all, and
  // out of the click handler, leaving the switch dead. A theme that cannot be REMEMBERED must
  // still be usable, so both paths degrade instead of failing.
  it('still themes the page when localStorage is unavailable', () => {
    const denied = () => {
      throw new DOMException('The operation is insecure.', 'SecurityError')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(denied)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(denied)
    systemPrefers('dark')

    // The boot script falls through the failed read to the OS preference...
    expect(loadPage()).toBe('dark')
    // ...and so does the store's own resolution. The attribute is cleared first so that
    // `currentTheme()` cannot short-circuit on it and skip the read being tested.
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
    resetTheme()
    expect(themeSnapshot()).toBe('dark')
    // A switch still lands on the document, it just is not remembered.
    expect(() => setTheme('light')).not.toThrow()
    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, 'light')

    vi.restoreAllMocks()
  })

  // Re-selecting the active theme is a no-op for subscribers but NOT for the document: the
  // attribute is re-asserted every time, which is what stops the store and <html> from drifting
  // apart if anything else ever writes to it.
  it('does not notify subscribers when the theme is unchanged', () => {
    systemPrefers('light')
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
    resetTheme()
    const listener = vi.fn()
    const unsubscribe = subscribeTheme(listener)

    setTheme('light')
    expect(listener).not.toHaveBeenCalled()
    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, 'light')

    setTheme('dark')
    expect(listener).toHaveBeenCalledTimes(1)

    unsubscribe()
    setTheme('light')
    expect(listener).toHaveBeenCalledTimes(1)
  })

  // The safety net for a page whose inline script never ran — a Content-Security-Policy that
  // forbids inline script would otherwise leave the app permanently light with no error anywhere.
  it('re-asserts the attribute from the entry point', () => {
    systemPrefers('dark')
    resetTheme()
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)

    initTheme()

    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, 'dark')
  })

  // The key is user-writable from a console and survives a deploy that renames a theme. An
  // unvalidated read would put `data-theme="sepia"` on <html>, matching no block: every token
  // would silently resolve to its light value while the attribute claimed otherwise.
  it('ignores an unrecognised stored value rather than putting it on the document', () => {
    systemPrefers('dark')
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    expect(loadPage()).toBe('dark')
  })
})
