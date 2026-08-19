import { Navbar } from '../../../shared/components/navbar/Navbar'

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

// The landing's top bar. It is the shared `Navbar` in its `flat` shell — the design draws ONE bar
// for the whole product (Figma `Navbar/Variant5`, node 1086:4929) and the four hand-rolled headers
// this file used to be one of had already drifted apart. What is left here is the landing's own
// three actions and the rule for which of them a visitor sees.
export function Header({
  onPrimaryCtaClick,
  isAuthenticated,
  onLogoutClick,
  onLoginClick,
  onHistoryClick,
}: HeaderProps) {
  return (
    <Navbar
      variant="flat"
      profileMenu={
        // Shown only to a signed-in user: a sign-out action on the public landing offers to end a
        // session that does not exist.
        isAuthenticated === true && onLogoutClick !== undefined
          ? { onLogoutClick, testIdPrefix: 'header' }
          : undefined
      }
      actions={
        <>
          {isAuthenticated !== true && (
            // The mockup's second header action for a signed-out visitor (01-landing.html:46,
            // "Вход", secondary next to the primary CTA). Returning users need a door that is not
            // "start something new" — without it, signing in meant knowing to type /login.
            <button
              type="button"
              className="btn-ghost header-login"
              data-testid="header-login-button"
              onClick={onLoginClick}
            >
              Войти
            </button>
          )}
          {isAuthenticated === true && (
            // The one entry point to work that exists only once you are signed in. Labelled for
            // the screen it opens: that step has been «Мои проекты» since story 12, and the
            // button kept the name of the list it replaced — the same door, announced under two
            // names depending on which side of it you stood on.
            <button
              type="button"
              className="btn-ghost header-history"
              data-testid="header-history-button"
              onClick={onHistoryClick}
            >
              Мои проекты
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
        </>
      }
    />
  )
}
