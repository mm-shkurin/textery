import { accountInitials } from '../../session/accountEmail'
import type { IdentityState } from '../../identity/identityStore'
import { useAvatarUrl } from '../../identity/useAvatarUrl'
import profileMenuStyles from './ProfileMenu.module.css'
import navbarStyles from '../navbar/Navbar.module.css'
import { AvatarAlertGlyph, AvatarPersonGlyph, AvatarPicture } from './profileAvatarGlyphs'

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
// Which of the three discs the identity is currently drawing. The modifier is the only visible
// difference between a request in flight and one that failed, so it is derived in one place
// rather than spelled out at the class site.
function discClassName(size: ProfileAvatarProps['size'], status: IdentityState['status']): string {
  const modifier =
    status === 'failed'
      ? ' ' + profileMenuStyles['profile-avatar-degraded']
      : status === 'ready'
        ? ''
        : ' ' + profileMenuStyles['profile-avatar-placeholder']
  return `${profileMenuStyles['profile-avatar']} ${
    profileMenuStyles[`profile-avatar-${size}`]
  } ${navbarStyles[`profile-avatar-${size}`] ?? ''}${modifier}`
}

// What goes inside the disc, in the order the three states are decided: a picture only for an
// identity that is CURRENTLY ready (drawing it over a loading or a degraded disc would put the
// previous account's face on the next account's header), then the failure glyph, then the
// initials or the neutral figure that stands in for them.
function DiscContent({
  identity,
  pictureUrl,
}: {
  identity: IdentityState
  pictureUrl: string | null
}) {
  const initials = identity.profile === null ? '' : accountInitials(identity.profile)
  if (identity.status === 'ready' && pictureUrl !== null) return <AvatarPicture url={pictureUrl} />
  if (identity.status === 'failed') return <AvatarAlertGlyph />
  if (initials === '') return <AvatarPersonGlyph />
  return <>{initials}</>
}

export function ProfileAvatar({ identity, size }: ProfileAvatarProps) {
  // Shared across every mounted avatar: one fetch for the page, one object URL, one revoke.
  const pictureUrl = useAvatarUrl()

  return (
    <span
      className={discClassName(size, identity.status)}
      data-testid={`profile-avatar-${identity.status}`}
      aria-hidden="true"
    >
      <DiscContent identity={identity} pictureUrl={pictureUrl} />
    </span>
  )
}
