import { accountInitials } from '../../../features/auth/utils/accountEmail'

interface ProfileAvatarProps {
  email: string | null
  // 'trigger' is the 44px circle in the navbar, 'menu' the 28px one inside the dropdown header.
  // A size *number* here would put a magic 44/28 at every call site; the two sizes are the design's
  // two roles, and the stylesheet owns what each measures.
  size: 'trigger' | 'menu'
}

// The gradient disc with the account's initials — Figma `Button/Container` (node 573:4506) and the
// same disc reused at 28px inside `Items/menu item` (node 823:4935).
//
// A signed-in account with no readable address still gets a disc: the menu's trigger must be
// findable in the corner whether or not the token carried an `email` claim. It gets a neutral
// glyph rather than a fabricated letter — a placeholder initial would be indistinguishable from a
// real one, and the user would read it as somebody else's account.
export function ProfileAvatar({ email, size }: ProfileAvatarProps) {
  const initials = email === null ? '' : accountInitials(email)

  return (
    <span className={`profile-avatar profile-avatar-${size}`} aria-hidden="true">
      {initials === '' ? (
        <svg viewBox="0 0 24 24" fill="none" focusable="false">
          <circle cx="12" cy="8.5" r="3.75" fill="currentColor" />
          <path
            d="M4.75 19.25c0-3.31 3.25-5.5 7.25-5.5s7.25 2.19 7.25 5.5"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        initials
      )}
    </span>
  )
}
