import profileMenuStyles from './ProfileMenu.module.css'
import navbarStyles from '../navbar/Navbar.module.css'

// The glyphs the profile menu draws, inline rather than as files under /design: each is a
// handful of path data, and an <img> for each would be more network requests for shapes that
// must recolour with the text around them (`currentColor` cannot cross an <img> boundary).

// The «Мой профиль» row (mockup 07, lucide `user`).
export function ProfileItemIcon() {
  return (
    <svg
      className={profileMenuStyles['profile-menu-icon']}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="8" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M3 13.25c0-2.2 2.24-3.5 5-3.5s5 1.3 5 3.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  )
}

// Figma `Icons/Set 24px` (node 676:4256) — the chevron beside the avatar, pointing at the menu:
// up while it is open, down while it is closed, because it points AT the panel, not at an action.
export function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={`${profileMenuStyles['profile-chevron']} ${navbarStyles['profile-chevron']}${
        expanded ? ' ' + profileMenuStyles['profile-chevron-up'] : ''
      }`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M7 10l5 5 5-5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Figma `Icons/Set 24px` inside the «Выйти» row (node 823:5017) — a door with an arrow leaving it.
export function SignOutIcon() {
  return (
    <svg
      className={profileMenuStyles['profile-menu-icon']}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M6.5 2.5H3.5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h3"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M10 5.25 12.75 8 10 10.75M12.5 8H6"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
