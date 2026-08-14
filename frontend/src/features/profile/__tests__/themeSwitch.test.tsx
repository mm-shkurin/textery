import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProfileThemeSwitch } from '../components/ProfileThemeSwitch'
import { THEME_ATTRIBUTE, THEME_STORAGE_KEY } from '../../../shared/theme/theme'
import { resetTheme } from '../../../shared/theme/themeStore'

// The «Внешний вид» switch — Figma node 1127:10768.
//
// Its third position is the interesting one: «Системная» is stored as the ABSENCE of a choice, so
// that a visitor who picks it gets the OS's answer on every later load rather than today's answer
// frozen into storage.
describe('the theme switch', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
    resetTheme()
  })

  it('starts on «Системная» when nothing was ever chosen', () => {
    render(<ProfileThemeSwitch />)

    expect(screen.getByTestId('profile-theme-system')).toBeChecked()
    expect(screen.getByTestId('profile-theme-light')).not.toBeChecked()
  })

  it('paints the page and remembers an explicit choice', () => {
    render(<ProfileThemeSwitch />)

    fireEvent.click(screen.getByTestId('profile-theme-dark'))

    expect(document.documentElement).toHaveAttribute(THEME_ATTRIBUTE, 'dark')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(screen.getByTestId('profile-theme-dark')).toBeChecked()
  })

  // The regression this file exists for: the selection has to move even when the PAGE does not.
  // Choosing «Светлая» on a light page repaints nothing, and a switch wired to the painted theme
  // would sit on «Системная» while storage said otherwise.
  it('moves off «Системная» even when the painted theme does not change', () => {
    render(<ProfileThemeSwitch />)
    expect(screen.getByTestId('profile-theme-system')).toBeChecked()

    fireEvent.click(screen.getByTestId('profile-theme-light'))

    expect(screen.getByTestId('profile-theme-light')).toBeChecked()
    expect(screen.getByTestId('profile-theme-system')).not.toBeChecked()
  })

  // Going back to «Системная» must REMOVE the key rather than write 'system' into it: the inline
  // boot script in index.html knows two values, and a third would resolve to no theme at all.
  it('forgets the stored choice when the system is chosen again', () => {
    render(<ProfileThemeSwitch />)
    fireEvent.click(screen.getByTestId('profile-theme-dark'))

    fireEvent.click(screen.getByTestId('profile-theme-system'))

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull()
    expect(screen.getByTestId('profile-theme-system')).toBeChecked()
  })
})
