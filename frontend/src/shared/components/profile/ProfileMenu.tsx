import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useIdentity } from '../../identity/useIdentity'
import { identityLabel } from '../../identity/identityLabel'
import { useDismissOnOutside } from '../../hooks/useDismissOnOutside'
import { ProfileAvatar } from './ProfileAvatar'
import { ProfileMenuIdentityRow } from './ProfileMenuIdentityRow'
import { ChevronIcon, ProfileItemIcon, SignOutIcon } from './profileMenuIcons'
import './ProfileMenu.css'

interface ProfileMenuProps {
  onLogoutClick: () => void
  // Several of these can be on screen across the app (the landing header, an app header, the
  // profile screen's own navbar), and a test that clicks «Выйти» must be able to say WHICH one.
  // The prefix is required rather than defaulted: a default would silently give both instances
  // the same id the first time a third screen adopted the menu.
  testIdPrefix: string
}

// The signed-in account in the top-right corner — Figma group `profile navbar` (node 1218:5171).
//
// Sign-out is not a top-level action: it is the rarest thing a signed-in user does, and behind the
// avatar it stays one click away without being the loudest control on the screen.
//
// «Мой профиль» sits ABOVE «Выйти». It was deliberately left out when this menu was built — the
// screen it points at did not exist, and a link to nowhere belongs to the story that builds the
// screen. Story 13 built it, so the item arrives with it.
//
// TWO RULES this component must not lose, both of which the /me move created:
//
//  1. «Выйти» NEVER depends on the profile request. The menu renders, opens, and offers the way
//     out whatever `/me` did. Gating its contents on a successful fetch locks a user inside a
//     session they cannot end, on the exact failure where they most want to leave.
//  2. The identity row is TEXT. `name` is free user input rendered in the header of every
//     authenticated page — the widest stored-XSS surface in the product. React escapes children
//     and attributes by default; the only way to lose that is to reach for
//     `dangerouslySetInnerHTML`, here or on the avatar's aria-label. Never.
export function ProfileMenu({ onLogoutClick, testIdPrefix }: ProfileMenuProps) {
  const identity = useIdentity()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  // Focus goes back to the trigger, not nowhere. Dismissing the panel destroys whatever inside it
  // held focus, and the browser then parks focus on <body> — a keyboard user would be dropped at
  // the top of the document, having to tab all the way back to where they were.
  const close = useCallback(() => {
    setOpen(false)
    triggerRef.current?.focus()
  }, [])

  useDismissOnOutside(open, containerRef, close)

  const label = identity.profile === null ? null : identityLabel(identity.profile)

  return (
    <div className="profile-menu" ref={containerRef}>
      <button
        type="button"
        ref={triggerRef}
        className="profile-trigger"
        data-testid={`${testIdPrefix}-profile-button`}
        aria-haspopup="menu"
        aria-expanded={open}
        // The avatar is a picture of initials, so it names nothing on its own. The identity makes
        // the control identifiable when several accounts are open in different tabs. Plain string
        // interpolation into a prop — React escapes attribute values too.
        aria-label={label === null ? 'Меню профиля' : `Меню профиля: ${label}`}
        onClick={() => setOpen((wasOpen) => !wasOpen)}
      >
        <ProfileAvatar identity={identity} size="trigger" />
        <ChevronIcon expanded={open} />
      </button>

      {open && (
        <div className="profile-panel" role="menu" data-testid={`${testIdPrefix}-profile-menu`}>
          <ProfileMenuIdentityRow identity={identity} testIdPrefix={testIdPrefix} />

          <button
            type="button"
            role="menuitem"
            className="profile-panel-item"
            data-testid={`${testIdPrefix}-profile-link`}
            onClick={() => {
              setOpen(false)
              navigate('/profile')
            }}
          >
            <ProfileItemIcon />
            Мой профиль
          </button>

          <button
            type="button"
            role="menuitem"
            className="profile-panel-item"
            data-testid={`${testIdPrefix}-logout-button`}
            onClick={() => {
              // Closed before the action, not after: signing out unmounts the screen this menu
              // lives on, and leaving the panel open until then means the last frame before the
              // landing still shows a menu for a session that has ended.
              setOpen(false)
              onLogoutClick()
            }}
          >
            <SignOutIcon />
            Выйти
          </button>
        </div>
      )}
    </div>
  )
}
