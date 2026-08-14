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
  // The wrapper is what carries the air above the bar. Put on the bar itself it would be padding
  // inside a plate that paints a background, growing the white rather than the gap; put as a
  // margin it escaped through `.profile-screen`, which has no padding or border of its own, and
  // opened a 24px band of page background above the header.
  return (
    <div className="navbar-profile-placement">
      <Navbar
        variant="pill"
        testId="profile-navbar"
        profileMenu={{ onLogoutClick, testIdPrefix: 'profile' }}
      />
    </div>
  )
}
