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
      <img className="app-logo" src="/logo.svg" alt="Textery" />
      {onLogoutClick && (
        <button
          type="button"
          className="app-logout"
          data-testid="workspace-logout-button"
          onClick={onLogoutClick}
        >
          Выйти
        </button>
      )}
    </header>
  )
}
