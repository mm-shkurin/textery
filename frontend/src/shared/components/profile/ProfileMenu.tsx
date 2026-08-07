import { useCallback, useRef, useState } from 'react'
import { useAccountEmail } from '../../../features/auth/hooks/useAccountEmail'
import { useDismissOnOutside } from '../../hooks/useDismissOnOutside'
import { ProfileAvatar } from './ProfileAvatar'
import { ChevronIcon, SignOutIcon } from './profileMenuIcons'
import './ProfileMenu.css'

interface ProfileMenuProps {
  onLogoutClick: () => void
  // Two of these can be on screen across the app (the landing header and an app header), and a
  // test that clicks «Выйти» must be able to say WHICH one. The prefix is required rather than
  // defaulted: a default would silently give both instances the same id the first time a third
  // screen adopted the menu.
  testIdPrefix: string
}

// The signed-in account in the top-right corner — Figma group `profile navbar` (node 1218:5171).
//
// It replaces the bare «Выйти» button that used to sit in both headers. Sign-out is not a
// top-level action: it is the rarest thing a signed-in user does, and it was competing for the
// corner with the actions they came for. Behind the avatar it stays one click away and stops
// being the loudest control on the screen.
//
// The dropdown's header row shows the address the token carries and nothing else. The design also
// draws «Базовый тариф» and a «Мой профиль» item; there is no tariff in the domain and no profile
// screen in the app, so both would be a label with nothing behind it and a link to nowhere.
// They belong to the story that builds those screens.
export function ProfileMenu({ onLogoutClick, testIdPrefix }: ProfileMenuProps) {
  const email = useAccountEmail()
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
    <div className="profile-menu" ref={containerRef}>
      <button
        type="button"
        ref={triggerRef}
        className="profile-trigger"
        data-testid={`${testIdPrefix}-profile-button`}
        aria-haspopup="menu"
        aria-expanded={open}
        // The avatar is a picture of initials, so it names nothing on its own. The address makes
        // the control identifiable when several accounts are open in different tabs.
        aria-label={email === null ? 'Меню профиля' : `Меню профиля: ${email}`}
        onClick={() => setOpen((wasOpen) => !wasOpen)}
      >
        <ProfileAvatar email={email} size="trigger" />
        <ChevronIcon expanded={open} />
      </button>

      {open && (
        <div className="profile-panel" role="menu" data-testid={`${testIdPrefix}-profile-menu`}>
          {email !== null && (
            // Not a menu item: it is the answer to "whose account am I in", and giving it
            // `role="menuitem"` would announce an identity label as something to activate.
            <div className="profile-panel-account">
              <ProfileAvatar email={email} size="menu" />
              <span className="profile-panel-email" data-testid={`${testIdPrefix}-profile-email`}>
                {email}
              </span>
            </div>
          )}

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
