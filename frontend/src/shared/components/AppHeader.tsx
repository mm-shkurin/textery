import { ProfileMenu } from './profile/ProfileMenu'
import './AppHeader.css'

interface AppHeaderProps {
  // Optional so a screen that has no session to end (or has not wired one yet) renders the
  // header exactly as before. Story 7 put sign-out in the workspace header; Story 5 had
  // already extracted that header to here, so this is where the action belongs — a second
  // inline header next to this one would drift the moment either changed.
  onLogoutClick?: () => void
}

export function AppHeader({ onLogoutClick }: AppHeaderProps) {
  return (
    <header className="app-header">
      <img className="app-logo" src="/design/logo-textery.svg" alt="Textery" />
      {/* Sign-out lives inside the account menu here for the same reason it does on the landing:
          one control for "this is my account, and here is the way out of it", identical on every
          screen that has a session. */}
      {onLogoutClick && <ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="workspace" />}
    </header>
  )
}
