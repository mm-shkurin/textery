/**
 * The five props the landing's top bar needs, declared once.
 *
 * `Header` renders them, `LandingPage` forwards them, and `FlowLanding` forwards
 * them again — three files that had each written the same five lines out. They are
 * one thing: what the landing's chrome can DO, which is a single decision made by
 * the gate in `App` and passed down.
 *
 * A shared type rather than three copies because these are a contract between
 * layers, not a coincidence: adding a sixth action should break every forwarder
 * that has not been updated, and three independent interfaces let two of them keep
 * compiling while silently dropping it.
 */
export interface LandingChromeProps {
  onPrimaryCtaClick?: () => void
  /**
   * Signed-in state is passed in rather than read from the session here: the header
   * is a presentational landing component, and the gate that owns this decision is
   * `App`'s. One reader means one place to be wrong.
   */
  isAuthenticated?: boolean
  onLogoutClick?: () => void
  onLoginClick?: () => void
  onHistoryClick?: () => void
}
