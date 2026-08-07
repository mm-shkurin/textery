import { ProfileMenu } from '../../../shared/components/profile/ProfileMenu'
import './Header.css'

interface HeaderProps {
  onPrimaryCtaClick?: () => void
  // Signed-in state is passed in rather than read from the session here: the header is a
  // presentational landing component, and the gate that owns this decision is App's. One
  // reader means one place to be wrong.
  isAuthenticated?: boolean
  onLogoutClick?: () => void
  onLoginClick?: () => void
  onHistoryClick?: () => void
}

export function Header({
  onPrimaryCtaClick,
  isAuthenticated,
  onLogoutClick,
  onLoginClick,
  onHistoryClick,
}: HeaderProps) {
  return (
    <header className="site-header">
      {/* Exported from the Figma `Logo` component (node 577:2034) rather than redrawn, so the
          mark stays byte-identical to the design source. */}
      <img className="brand-logo" src="/design/logo-textery.svg" alt="Textery" />
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
          // Both history endpoints 401 without a token, so this is the one entry point to work
          // that only exists once you are signed in. Signed-out visitors are not shown a door
          // to an empty room.
          <button
            type="button"
            className="btn-ghost header-history"
            data-testid="header-history-button"
            onClick={onHistoryClick}
          >
            Мои работы
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
        {isAuthenticated && onLogoutClick !== undefined && (
          // Shown only to a signed-in user: a sign-out action on the public landing offers to end
          // a session that does not exist. It moved INTO the avatar menu (Figma `profile navbar`,
          // node 1218:5171) — the earlier note here said the client never stores the email, which
          // is no longer the reason to omit it: the access token carries an `email` claim, so the
          // menu shows the real address rather than an invented one.
          //
          // Last in the row, right of the CTA: the account is the corner of the header, and the
          // design puts it at the far edge on every screen that has one.
          <ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="header" />
        )}
      </div>
    </header>
  )
}
