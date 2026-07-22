import './LoginForm.css'

// OAuth providers as DATA, not duplicated JSX branches: an unknown provider is simply not in this
// array, so it is not a reachable code path. Each entry is a full-page navigation (an <a>, not a
// fetch) to the backend start endpoint — the client never talks to a provider SDK. The badge is
// DECORATIVE (aria-hidden) so each control's accessible name is exactly its label.
const OAUTH_PROVIDERS = [
  { provider: 'vk', label: 'Войти через VK ID', badge: 'VK', startPath: '/api/v1/auth/oauth/vk/start' },
  { provider: 'yandex', label: 'Войти через Yandex ID', badge: 'Я', startPath: '/api/v1/auth/oauth/yandex/start' },
] as const

export function OAuthProviderButtons() {
  return (
    <>
      <div className="auth-divider">или</div>
      <div className="oauth-list">
        {OAUTH_PROVIDERS.map(({ provider, label, badge, startPath }) => (
          <a
            key={provider}
            className={`btn-oauth btn-oauth-${provider}`}
            href={startPath}
            data-testid={`oauth-${provider}-button`}
          >
            <span className={`provider-badge provider-badge-${provider}`} aria-hidden="true">
              {badge}
            </span>
            {label}
          </a>
        ))}
      </div>
    </>
  )
}
