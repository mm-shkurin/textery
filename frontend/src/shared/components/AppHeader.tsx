import { Navbar } from './navbar/Navbar'

interface AppHeaderProps {
  // Optional so a screen that has no session to end (or has not wired one yet) renders the
  // header exactly as before. Story 7 put sign-out in the workspace header; Story 5 had
  // already extracted that header to here, so this is where the action belongs — a second
  // inline header next to this one would drift the moment either changed.
  onLogoutClick?: () => void
}

// The workspace and editor bar. Kept as its own name rather than replaced at the call sites: the
// generation screens import `AppHeader`, and this wrapper lets the markup underneath become the
// shared `Navbar` without editing them. The bar itself is the same object as every other screen's.
export function AppHeader({ onLogoutClick }: AppHeaderProps) {
  return (
    <Navbar
      variant="bar"
      // Sign-out lives inside the account menu here for the same reason it does on the landing:
      // one control for "this is my account, and here is the way out of it", identical on every
      // screen that has a session.
      profileMenu={
        onLogoutClick === undefined ? undefined : { onLogoutClick, testIdPrefix: 'workspace' }
      }
    />
  )
}
