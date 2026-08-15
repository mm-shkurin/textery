import { useTheme } from '../../theme/useTheme'
import { toggleTheme } from '../../theme/themeStore'
import './ThemeSwitch.css'

// The theme control for a signed-OUT visitor.
//
// The existing switch is a row of the account menu, which is behind the avatar, which is behind
// the auth gate — so a guest had no way to change the theme at all. That is not a missing nicety:
// the choice is stored per device by `themeStore`, and a visitor who prefers dark had to create
// an account before the product would stop being bright at them.
//
// A track-and-knob rather than a copy of the menu row: it sits in a bar next to two buttons with
// labels, and a third labelled control there would compete with «Войти» for the same glance. The
// switch reads as a setting, not as an action.
//
// `role="switch"` with `aria-checked` — the same reasoning as the menu's `menuitemcheckbox`. A
// plain button announces "тёмная тема" with no hint of which way it is set, and the only way to
// find out would be to press it, which is the one act that changes the answer.
export function ThemeSwitch() {
  const theme = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? 'Тёмная тема включена' : 'Тёмная тема выключена'}
      className="theme-switch"
      data-testid="theme-switch"
      onClick={toggleTheme}
    >
      {/* Both glyphs are always rendered, one on each end of the track, and the knob slides over
          the one that is active. Swapping a single glyph would make the control state the theme
          it is IN, which reads to half of users as the theme it would switch TO. */}
      <SunIcon />
      <MoonIcon />
      <span className="theme-switch-knob" aria-hidden="true" />
    </button>
  )
}

function SunIcon() {
  return (
    <svg
      className="theme-switch-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M3 12h2M19 12h2M6.6 17.4l-1.4 1.4M18.8 5.2l-1.4 1.4" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg
      className="theme-switch-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
    </svg>
  )
}
