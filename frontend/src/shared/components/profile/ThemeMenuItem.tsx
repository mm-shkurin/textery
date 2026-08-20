import { useTheme } from '../../theme/useTheme'
import { toggleTheme } from '../../theme/themeStore'
import profileMenuStyles from './ProfileMenu.module.css'

// The theme switch, as a row of the account menu — Figma has no node for it; it follows
// «Мой профиль» and sits ABOVE «Выйти», because «Выйти» must stay the last thing in the panel:
// it is the one item whose position users hit by muscle memory.
//
// A SEPARATE FILE rather than more JSX inside ProfileMenu.tsx. That file is being edited in
// parallel for the avatar work, and a switch that arrives as one import plus one element is a
// merge this story does not have to referee.
//
// `menuitemcheckbox`, not `menuitem`. This is a two-state control, and a plain menuitem announces
// «Тема: тёмная» with no indication that it is a toggle or which way it is currently set — a
// screen-reader user would have to activate it to find out, which is the one action that changes
// the answer. `aria-checked` says it out loud.
//
// No `useState`: the theme lives on <html> and in the store, and a local copy would drift from
// both the moment a second menu is mounted (the app header and the profile screen's own navbar
// are on screen together).
export function ThemeMenuItem({ testIdPrefix }: { testIdPrefix: string }) {
  const theme = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={isDark}
      className={profileMenuStyles['profile-panel-item']}
      data-testid={`${testIdPrefix}-theme-toggle`}
      // The panel deliberately STAYS OPEN. Unlike «Мой профиль» and «Выйти», which navigate away,
      // this changes the page underneath the menu — closing it would hide the result of the click
      // behind the click's own side effect, and a user comparing the two themes would have to
      // reopen the menu for every comparison.
      onClick={toggleTheme}
    >
      <ThemeIcon dark={isDark} />
      {isDark ? 'Тема: тёмная' : 'Тема: светлая'}
    </button>
  )
}

// Drawn here rather than added to `profileMenuIcons.tsx` for the same merge reason as above. Both
// glyphs are `currentColor` so they inherit the row's text colour in either theme.
function ThemeIcon({ dark }: { dark: boolean }) {
  return (
    <svg
      className={profileMenuStyles['profile-menu-icon']}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      // The icon repeats what the label already says, so it is decorative to a screen reader.
      aria-hidden="true"
    >
      {dark ? (
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
      ) : (
        <>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </>
      )}
    </svg>
  )
}
