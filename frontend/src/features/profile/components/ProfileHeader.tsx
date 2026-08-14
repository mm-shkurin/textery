import { Navbar } from '../../../shared/components/navbar/Navbar'
import '../../../shared/components/navbar/NavbarPlacement.css'

interface ProfileHeaderProps {
  onLogoutClick: () => void
}

// The profile screen's top bar — the shared `Navbar` in its `pill` shell, aligned to this screen's
// 1240px column instead of the feed's 1640. The width was the whole reason this used to be its own
// six lines of markup; as a placement class it no longer needs a component of its own.
//
// The account menu is unconditional here: the screen is behind the auth gate, and «Выйти» must be
// reachable even when the profile request has failed — that is the state the user is most likely
// to want out of.
export function ProfileHeader({ onLogoutClick }: ProfileHeaderProps) {
  return (
    <Navbar
      variant="pill"
      className="navbar-profile-placement"
      testId="profile-navbar"
      profileMenu={{ onLogoutClick, testIdPrefix: 'profile' }}
    />
  )
}
