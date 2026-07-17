import './Header.css'

interface HeaderProps {
  onPrimaryCtaClick?: () => void
  // Signed-in state is passed in rather than read from the session here: the header is a
  // presentational landing component, and the gate that owns this decision is App's. One
  // reader means one place to be wrong.
  isAuthenticated?: boolean
  onLogoutClick?: () => void
  onLoginClick?: () => void
}

export function Header({
  onPrimaryCtaClick,
  isAuthenticated,
  onLogoutClick,
  onLoginClick,
}: HeaderProps) {
  return (
    <header className="site-header">
      <img className="brand-logo" src="/logo.svg" alt="Textery" />
      <div className="header-actions">
        {!isAuthenticated && (
          // The mockup's second header action for a signed-out visitor (01-landing.html:46,
          // "Вход", secondary next to the primary CTA). Returning users need a door that is
          // not "start something new" — without it, signing in meant knowing to type /login.
          <button
            type="button"
            className="btn-ghost header-login"
            data-testid="header-login-button"
            onClick={onLoginClick}
          >
            Войти
          </button>
        )}
        {isAuthenticated && (
          // Shown only to a signed-in user: a "Выйти" button on the public landing offers to
          // end a session that does not exist. The mockup (05-authenticated.html) draws a user
          // menu with an email here, but the client never stores the email — inventing one to
          // fill the pill would be placeholder data on a real screen. A plain sign-out action
          // is the honest subset until the account menu has something true to show.
          <button
            type="button"
            className="btn-ghost header-logout"
            data-testid="header-logout-button"
            onClick={onLogoutClick}
          >
            Выйти
          </button>
        )}
        <button
          type="button"
          className="btn-light"
          data-testid="header-primary-cta-button"
          onClick={onPrimaryCtaClick}
        >
          Создать генерацию
        </button>
      </div>
    </header>
  )
}
