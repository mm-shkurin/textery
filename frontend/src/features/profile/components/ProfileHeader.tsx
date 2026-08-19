import { Navbar } from '../../../shared/components/navbar/Navbar'
import '../../../shared/components/navbar/NavbarPlacement.css'

interface ProfileHeaderProps {
  onLogoutClick: () => void
  // The way back to the feed. Optional so the bar can still be rendered by a test that does not
  // care about navigation; without it the button is simply absent rather than dead.
  onProjectsClick?: () => void
}

// The profile screen's top bar — the shared `Navbar` in its `pill` shell, on the same 1640px
// column as the cards under it (node 1134:12269).
//
// The bar carries «Мои проекты» as its one action, which is what the frame draws and what makes
// the screen leavable. It replaces the «Назад» button that used to sit under the header: two
// controls doing the same thing, one of them where the design has none.
//
// The account menu is unconditional here: the screen is behind the auth gate, and «Выйти» must be
// reachable even when the profile request has failed — that is the state the user is most likely
// to want out of.
export function ProfileHeader({ onLogoutClick, onProjectsClick }: ProfileHeaderProps) {
  // The wrapper is what carries the air above the bar. Put on the bar itself it would be padding
  // inside a plate that paints a background, growing the white rather than the gap; put as a
  // margin it escaped through `.profile-screen`, which has no padding or border of its own, and
  // opened a 24px band of page background above the header.
  return (
    <div className="navbar-profile-placement">
      <Navbar
        variant="pill"
        testId="profile-navbar"
        actions={
          onProjectsClick === undefined ? undefined : (
            <button
              type="button"
              className="btn-light"
              data-testid="profile-to-projects"
              onClick={onProjectsClick}
            >
              Мои проекты
            </button>
          )
        }
        profileMenu={{ onLogoutClick, testIdPrefix: 'profile' }}
      />
    </div>
  )
}
