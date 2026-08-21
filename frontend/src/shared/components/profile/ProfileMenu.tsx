import { useCallback, useRef, useState } from 'react'
import { useIdentity } from '../../identity/useIdentity'
import { identityLabel } from '../../identity/identityLabel'
import { useDismissOnOutside } from '../../hooks/useDismissOnOutside'
import { ProfileMenuPanel, ProfileMenuTrigger } from './ProfileMenuPanel'
import styles from './ProfileMenu.module.css'

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

  return (
    <div className={styles['profile-menu']} ref={containerRef}>
      <ProfileMenuTrigger
        identity={identity}
        label={identity.profile === null ? null : identityLabel(identity.profile)}
        open={open}
        triggerRef={triggerRef}
        testIdPrefix={testIdPrefix}
        onToggle={() => setOpen((wasOpen) => !wasOpen)}
      />
      {open && (
        <ProfileMenuPanel
          identity={identity}
          testIdPrefix={testIdPrefix}
          onClose={() => setOpen(false)}
          onLogoutClick={onLogoutClick}
        />
      )}
    </div>
  )
}
