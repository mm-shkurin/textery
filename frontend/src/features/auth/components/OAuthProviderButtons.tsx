import { OAUTH_PROVIDERS } from '../utils/oauthProviders'
import './LoginForm.css'

// OAuth providers as DATA, not duplicated JSX branches: an unknown provider is simply not in this
// list, so it is not a reachable code path. The list lives in utils/oauthProviders so the callback
// screen's malformed-guard shares the exact same provider set. Each entry is a full-page navigation
// (an <a>, not a fetch) to the backend start endpoint — the client never talks to a provider SDK.
// The badge is DECORATIVE (aria-hidden) so each control's accessible name is exactly its label.
export function OAuthProviderButtons() {
  return (
    <>
      <div className="auth-divider">или</div>
      <div className="oauth-list">
        {OAUTH_PROVIDERS.map(({ provider, label, badgeSrc, startPath }) => (
          <a
            key={provider}
            className={`btn-oauth btn-oauth-${provider}`}
            href={startPath}
            data-testid={`oauth-${provider}-button`}
          >
            <span className="provider-badge" aria-hidden="true">
              <img src={badgeSrc} alt="" />
            </span>
            {label}
          </a>
        ))}
      </div>
    </>
  )
}
