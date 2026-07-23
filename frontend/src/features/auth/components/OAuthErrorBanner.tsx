import { useLocation } from 'react-router-dom'
import { isUsableMessage } from '../utils/authMessages'
import './LoginForm.css'

// Surfaces the provider-aware message the /auth/callback error path stashes in router state
// (`location.state.oauthError`) as a DISTINCT banner: its own class + testid + role="alert",
// SEPARATE from the field-validation error (`login-form-error`) and the network error, so a
// provider sign-in failure never reads as "your password was wrong". Rendered at the top of the
// login card per mockup 03-login-oauth-error.html.
//
// isUsableMessage gates the render: no state, a non-string, or a blank string yields nothing, so a
// plain /login visit shows no banner at all.
export function OAuthErrorBanner() {
  const location = useLocation()
  const oauthError = (location.state as { oauthError?: unknown } | null)?.oauthError
  if (!isUsableMessage(oauthError)) {
    return null
  }
  return (
    <div className="auth-oauth-error" data-testid="login-oauth-error" role="alert">
      {/* Leading alert-circle (lucide glyph, inline so no icon dependency); aria-hidden and
          text-free so the banner's textContent stays exactly the message the tests pin. */}
      <svg
        className="auth-oauth-error-icon"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {oauthError}
    </div>
  )
}
