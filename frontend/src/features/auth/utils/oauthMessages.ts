// Provider-aware copy for an OAuth sign-in that came back with an `?error` (a provider fault or a
// user-cancel), routed from the /auth/callback interstitial to /login. Exact copy from mockup
// 03-login-oauth-error.html. Kept in utils/ (mocked by nothing) beside authMessages.ts.
//
// The provider value arrives from the callback query string — attacker-influenceable. It is NEVER
// interpolated into user-facing copy: the mapper only ever returns one of these three fixed
// strings, matched on an exact provider id, so an unknown or crafted provider falls through to the
// GENERIC message rather than reflecting its raw value onto the screen.
export const OAUTH_VK_FAILURE_MESSAGE = 'Не удалось войти через VK ID. Попробуйте снова.'
export const OAUTH_YANDEX_FAILURE_MESSAGE = 'Не удалось войти через Yandex ID. Попробуйте снова.'
export const OAUTH_GENERIC_FAILURE_MESSAGE = 'Не удалось войти через провайдера. Попробуйте снова.'

// Exact-match only: VK for exactly 'vk', Yandex for exactly 'yandex', GENERIC for everything else
// (null, '', unknown ids). No interpolation of the raw provider — see module note above.
export function oauthProviderFailureMessage(provider: string | null): string {
  if (provider === 'vk') return OAUTH_VK_FAILURE_MESSAGE
  if (provider === 'yandex') return OAUTH_YANDEX_FAILURE_MESSAGE
  return OAUTH_GENERIC_FAILURE_MESSAGE
}
