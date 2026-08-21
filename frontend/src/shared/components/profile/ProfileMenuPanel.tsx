import type { RefObject } from 'react'
import { useNavigate } from 'react-router-dom'
import type { IdentityState } from '../../identity/identityStore'
import { ProfileAvatar } from './ProfileAvatar'
import { ProfileMenuIdentityRow } from './ProfileMenuIdentityRow'
import { ChevronIcon, ProfileItemIcon, SignOutIcon } from './profileMenuIcons'
import { ThemeMenuItem } from './ThemeMenuItem'
import profileMenuStyles from './ProfileMenu.module.css'

interface TriggerProps {
  identity: IdentityState
  // The avatar is a picture of initials, so it names nothing on its own. The identity makes the
  // control identifiable when several accounts are open in different tabs. Null when `/me` has
  // not answered — the control still opens, it just has no account to name yet.
  label: string | null
  open: boolean
  triggerRef: RefObject<HTMLButtonElement>
  testIdPrefix: string
  onToggle: () => void
}

export function ProfileMenuTrigger({
  identity,
  label,
  open,
  triggerRef,
  testIdPrefix,
  onToggle,
}: TriggerProps) {
  return (
    <button
      type="button"
      ref={triggerRef}
      className={profileMenuStyles['profile-trigger']}
      data-testid={`${testIdPrefix}-profile-button`}
      aria-haspopup="menu"
      aria-expanded={open}
      // Plain string interpolation into a prop — React escapes attribute values too.
      aria-label={label === null ? 'Меню профиля' : `Меню профиля: ${label}`}
      onClick={onToggle}
    >
      <ProfileAvatar identity={identity} size="trigger" />
      <ChevronIcon expanded={open} />
    </button>
  )
}

interface PanelProps {
  identity: IdentityState
  testIdPrefix: string
  // Both items close the panel before doing anything else — see ProfileMenu for why «Выйти» must.
  onClose: () => void
  onLogoutClick: () => void
}

export function ProfileMenuPanel({ identity, testIdPrefix, onClose, onLogoutClick }: PanelProps) {
  const navigate = useNavigate()
  return (
    <div
      className={profileMenuStyles['profile-panel']}
      role="menu"
      data-testid={`${testIdPrefix}-profile-menu`}
    >
      <ProfileMenuIdentityRow identity={identity} testIdPrefix={testIdPrefix} />

      <button
        type="button"
        role="menuitem"
        className={profileMenuStyles['profile-panel-item']}
        data-testid={`${testIdPrefix}-profile-link`}
        onClick={() => {
          onClose()
          navigate('/profile')
        }}
      >
        <ProfileItemIcon />
        Мой профиль
      </button>

      <ThemeMenuItem testIdPrefix={testIdPrefix} />

      <button
        type="button"
        role="menuitem"
        className={profileMenuStyles['profile-panel-item']}
        data-testid={`${testIdPrefix}-logout-button`}
        onClick={() => {
          // Closed before the action, not after: signing out unmounts the screen this menu
          // lives on, and leaving the panel open until then means the last frame before the
          // landing still shows a menu for a session that has ended.
          onClose()
          onLogoutClick()
        }}
      >
        <SignOutIcon />
        Выйти
      </button>
    </div>
  )
}
