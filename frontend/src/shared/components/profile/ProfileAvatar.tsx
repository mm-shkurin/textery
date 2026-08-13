import { accountInitials } from '../../../features/auth/utils/accountEmail'
import type { IdentityState } from '../../identity/identityStore'

interface ProfileAvatarProps {
  identity: IdentityState
  // 'trigger' is the 44px circle in the navbar, 'menu' the 28px one inside the dropdown header,
  // 'card' the 72px one on the profile screen. A size *number* here would put a magic 44/28/72 at
  // every call site; these are the design's three roles, and the stylesheet owns what each
  // measures.
  size: 'trigger' | 'menu' | 'card'
}

// The gradient disc with the account's initials — Figma `Button/Container` (node 573:4506) and the
// same disc reused at 28px inside `Items/menu item` (node 823:4935).
//
// It draws THREE visibly different things, and the difference is load-bearing (mockup 08 exists to
// pin it):
//   - loading  — a shimmering placeholder disc. Defined, never a blank circle that pops into
//     initials: since the header moved onto /me this state is every page for the length of a
//     request, not an edge case.
//   - failed   — a dashed disc with an alert glyph, STATIC. A failure that looked healthy would
//     read as "an account with no name", and one that looked like the placeholder would read as
//     "still loading" forever.
//   - ready    — the initials, from the name if there is one and from the address otherwise.
//
// A ready account with no derivable initials still gets a disc with a neutral glyph rather than a
// fabricated letter: a placeholder initial is indistinguishable from a real one, and the user
// would read it as somebody else's account.
export function ProfileAvatar({ identity, size }: ProfileAvatarProps) {
  const initials = identity.profile === null ? '' : accountInitials(identity.profile)
  const modifier =
    identity.status === 'failed'
      ? ' profile-avatar-degraded'
      : identity.status === 'ready'
        ? ''
        : ' profile-avatar-placeholder'

  return (
    <span
      className={`profile-avatar profile-avatar-${size}${modifier}`}
      data-testid={`profile-avatar-${identity.status}`}
      aria-hidden="true"
    >
      {identity.status === 'failed' ? (
        <svg viewBox="0 0 24 24" fill="none" focusable="false">
          <path
            d="M12 4.5 21 20H3L12 4.5Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
          <path d="M12 10v4.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <circle cx="12" cy="17.4" r="1" fill="currentColor" />
        </svg>
      ) : initials === '' ? (
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
