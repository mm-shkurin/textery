import { ProfileMenu } from '../../../shared/components/profile/ProfileMenu'

interface ProfileHeaderProps {
  onLogoutClick: () => void
}

// The profile screen's top bar. It is the «Мои проекты» navbar's shape — a white pill with the
// logo at one end and the account at the other — but at this screen's 1240px shell rather than
// that screen's 1640, so it is its own six lines instead of a width flag threaded through
// `ProjectsNavbar`.
//
// The account menu is unconditional here: the screen is behind the auth gate, and «Выйти» must be
// reachable even when the profile request has failed — that is the state the user is most likely
// to want out of.
export function ProfileHeader({ onLogoutClick }: ProfileHeaderProps) {
  return (
    <header className="profile-navbar" data-testid="profile-navbar">
      <img className="profile-navbar-logo" src="/design/logo-textery.svg" alt="Textery" />
      <ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="profile" />
    </header>
  )
}
